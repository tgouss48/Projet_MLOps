# Entrainement : baseline de persistance, regression logistique, gradient boosting
# Lancer avec : python src/train.py
import hashlib
import json
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
import yaml
from mlflow.models import infer_signature
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURES

TARGET = "target_peak_h1"


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def cost(y, pred, cost_fn, cost_fp):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return int(cost_fn * fn + cost_fp * fp)


def best_threshold(y, proba, cost_fn, cost_fp):
    # on teste tous les seuils et on garde celui qui coute le moins
    seuils = np.arange(0.05, 0.96, 0.01)
    couts = [cost(y, (proba >= s).astype(int), cost_fn, cost_fp) for s in seuils]
    return round(float(seuils[int(np.argmin(couts))]), 2)


def evaluate(y, proba, threshold, cost_fn, cost_fp):
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y, proba), 4),
        "cost": int(cost_fn * fn + cost_fp * fp),
        "fn": int(fn), "fp": int(fp), "tp": int(tp), "tn": int(tn),
    }


class Persistance:
    # baseline sans apprentissage : pic dans 1h si on est deja au dessus du seuil
    def __init__(self, peak_kw):
        self.peak_kw = peak_kw

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        p = (X["total_kw"] > self.peak_kw).astype(float).to_numpy()
        return np.column_stack([1 - p, p])


def make_models(p, peak_kw):
    return {
        "persistance": Persistance(peak_kw),
        "logreg": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=p["logreg"]["C"], solver="liblinear", random_state=p["random_state"]),
        ),
        "hgb": HistGradientBoostingClassifier(**p["hgb"], random_state=p["random_state"]),
    }


def main():
    params = yaml.safe_load(open("params.yaml"))
    p = params["train"]
    data_dir = Path(params["data"]["processed_dir"])
    peak_kw = json.load(open("reports/data_stats.json"))["peak_threshold_kw"]

    train = pd.read_csv(data_dir / "train.csv", parse_dates=["datetime"])
    test = pd.read_csv(data_dir / "test.csv", parse_dates=["datetime"])

    # validation = dernieres semaines du train (le test n'est pas utilise pour choisir)
    val_start = train["datetime"].max() - pd.Timedelta(days=p["val_days"])
    fit_part, val_part = train[train["datetime"] < val_start], train[train["datetime"] >= val_start]

    mlflow.set_tracking_uri(params["mlflow"]["tracking_uri"])
    mlflow.set_experiment(params["mlflow"]["experiment"])

    results = {}
    for name, model in make_models(p, peak_kw).items():
        with mlflow.start_run(run_name=name) as run:
            # 1) choix du seuil de decision sur la validation
            model.fit(fit_part[FEATURES], fit_part[TARGET])
            val_proba = model.predict_proba(val_part[FEATURES])[:, 1]
            if name == "persistance":
                threshold = 0.5
            else:
                threshold = best_threshold(val_part[TARGET], val_proba, p["cost_fn"], p["cost_fp"])
            val_metrics = evaluate(val_part[TARGET], val_proba, threshold, p["cost_fn"], p["cost_fp"])

            # 2) re-entrainement sur tout le train puis evaluation unique sur le test
            model.fit(train[FEATURES], train[TARGET])
            test_proba = model.predict_proba(test[FEATURES])[:, 1]
            test_metrics = evaluate(test[TARGET], test_proba, threshold, p["cost_fn"], p["cost_fp"])

            mlflow.log_params({"model": name, "decision_threshold": threshold, "peak_threshold_kw": peak_kw,
                               "cost_fn": p["cost_fn"], "cost_fp": p["cost_fp"], "val_days": p["val_days"]})
            if name in ("logreg", "hgb"):
                mlflow.log_params({f"{name}_{k}": v for k, v in p[name].items()})
            mlflow.log_metrics({f"val_{k}": v for k, v in val_metrics.items()})
            mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})
            mlflow.set_tags({"train_md5": md5(data_dir / "train.csv"), "test_md5": md5(data_dir / "test.csv")})

            results[name] = {"run_id": run.info.run_id, "model": model, "threshold": threshold,
                             "val": val_metrics, "test": test_metrics}
            print(f"{name:12s} seuil={threshold:.2f}  val_cout={val_metrics['cost']:5d}  "
                  f"test: rappel={test_metrics['recall']:.3f} precision={test_metrics['precision']:.3f} "
                  f"pr_auc={test_metrics['pr_auc']:.3f} cout={test_metrics['cost']}")

    # le modele retenu est celui qui a le plus petit cout sur la validation (pas sur le test)
    candidats = {k: v for k, v in results.items() if k != "persistance"}
    best_name = min(candidats, key=lambda k: candidats[k]["val"]["cost"])
    best = results[best_name]

    Path("models").mkdir(exist_ok=True)
    joblib.dump(best["model"], "models/model.joblib")
    meta = {
        "model": best_name,
        "mlflow_run_id": best["run_id"],
        "decision_threshold": best["threshold"],
        "peak_threshold_kw": peak_kw,
        "features": FEATURES,
        "train_md5": md5(data_dir / "train.csv"),
    }
    Path("models/metadata.json").write_text(json.dumps(meta, indent=2))

    metrics = {"best_model": best_name, "decision_threshold": best["threshold"], "test": best["test"],
               "baseline_test": results["persistance"]["test"],
               "all_models_val_cost": {k: v["val"]["cost"] for k, v in results.items()}}
    Path("reports/metrics.json").write_text(json.dumps(metrics, indent=2))

    with mlflow.start_run(run_id=best["run_id"]):
        example = test[FEATURES].head(3).astype(float)
        signature = infer_signature(example, best["model"].predict_proba(example)[:, 1])
        mlflow.sklearn.log_model(best["model"], "model", signature=signature, input_example=example)
        mlflow.log_artifact("models/metadata.json")
        mlflow.set_tag("selected", "true")

    print("modele retenu :", best_name)


if __name__ == "__main__":
    main()
