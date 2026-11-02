# Quality gate : le modele est accepte seulement si tous les controles passent
# Lancer avec : python src/quality_gate.py            (modele du pipeline, dossier models/)
#           ou : python src/quality_gate.py <dossier>  (autre modele candidat)
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
import yaml

from features import FEATURES
from train import TARGET, Persistance, evaluate


def check(name, value, seuil, ok):
    return {"controle": name, "valeur": value, "seuil": seuil, "ok": bool(ok)}


def run_checks(model, meta, test, peak_kw, g, cost_fn, cost_fp):
    checks = []

    # 1) controles techniques
    checks.append(check("features attendues", meta["features"] == FEATURES, True, meta["features"] == FEATURES))
    if meta["features"] != FEATURES:
        return checks
    proba = model.predict_proba(test[FEATURES])[:, 1]
    proba_ok = len(proba) == len(test) and not np.isnan(proba).any() and proba.min() >= 0 and proba.max() <= 1
    checks.append(check("probabilites valides", bool(proba_ok), True, proba_ok))

    x = test[FEATURES].head(1)
    debut = time.perf_counter()
    for _ in range(100):
        model.predict_proba(x)
    latence = round((time.perf_counter() - debut) * 10, 2)
    checks.append(check("latence moyenne (ms)", latence, g["max_latency_ms"], latence <= g["max_latency_ms"]))

    # 2) performances sur le test (recalculees ici, on ne fait pas confiance au fichier du train)
    seuil = meta["decision_threshold"]
    m = evaluate(test[TARGET], proba, seuil, cost_fn, cost_fp)
    checks.append(check("rappel", m["recall"], g["min_recall"], m["recall"] >= g["min_recall"]))
    checks.append(check("precision", m["precision"], g["min_precision"], m["precision"] >= g["min_precision"]))
    checks.append(check("pr_auc", m["pr_auc"], g["min_pr_auc"], m["pr_auc"] >= g["min_pr_auc"]))

    base = Persistance(peak_kw).predict_proba(test[FEATURES])[:, 1]
    cout_base = evaluate(test[TARGET], base, 0.5, cost_fn, cost_fp)["cost"]
    checks.append(check("cout < cout persistance", m["cost"], cout_base, m["cost"] < cout_base))

    # 3) sous-groupe : week-end
    we = test["is_weekend"] == 1
    m_we = evaluate(test.loc[we, TARGET], proba[we.to_numpy()], seuil, cost_fn, cost_fp)
    checks.append(check("rappel week-end", m_we["recall"], g["min_recall_weekend"], m_we["recall"] >= g["min_recall_weekend"]))
    return checks


def main():
    params = yaml.safe_load(open("params.yaml"))
    p = params["train"]
    model_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("models")
    report_path = "reports/quality_gate.json" if len(sys.argv) == 1 else f"reports/quality_gate_{model_dir.name}.json"

    model = joblib.load(model_dir / "model.joblib")
    meta = json.load(open(model_dir / "metadata.json"))
    test = pd.read_csv(Path(params["data"]["processed_dir"]) / "test.csv")
    peak_kw = json.load(open("reports/data_stats.json"))["peak_threshold_kw"]

    checks = run_checks(model, meta, test, peak_kw, params["gate"], p["cost_fn"], p["cost_fp"])
    accepte = all(c["ok"] for c in checks)

    report = {
        "decision": "ACCEPTE" if accepte else "REFUSE",
        "modele": meta["model"],
        "dossier": str(model_dir),
        "mlflow_run_id": meta.get("mlflow_run_id"),
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "controles": checks,
        "raisons_refus": [c["controle"] for c in checks if not c["ok"]],
    }
    Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))

    # on note la decision dans le run MLflow du modele
    if meta.get("mlflow_run_id"):
        mlflow.set_tracking_uri(params["mlflow"]["tracking_uri"])
        with mlflow.start_run(run_id=meta["mlflow_run_id"]):
            mlflow.set_tag("quality_gate", report["decision"])
            mlflow.log_artifact(report_path)

    for c in checks:
        print(f"[{'OK' if c['ok'] else 'KO'}] {c['controle']:25s} valeur={c['valeur']}  seuil={c['seuil']}")
    print("decision :", report["decision"], "->", report_path)
    if not accepte:
        sys.exit(1)


if __name__ == "__main__":
    main()
