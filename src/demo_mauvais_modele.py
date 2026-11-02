# Demo d'un refus par la quality gate.
# Scenario : un modele candidat entraine sans l'historique de consommation
# (uniquement meteo + calendrier). Il est plus simple mais beaucoup moins bon.
# Lancer avec : python src/demo_mauvais_modele.py  puis  python src/quality_gate.py models_refus
import json
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURES
from train import TARGET

SANS_CONSO = ["temperature", "humidity", "wind_speed", "general_diffuse_flows", "diffuse_flows",
              "hour_sin", "hour_cos", "dayofweek", "is_weekend"]


def main():
    params = yaml.safe_load(open("params.yaml"))
    train = pd.read_csv(Path(params["data"]["processed_dir"]) / "train.csv")

    # le modele recoit les memes colonnes que le vrai mais ignore celles de consommation
    model = make_pipeline(
        ColumnTransformer([("meteo_calendrier", StandardScaler(), SANS_CONSO)], remainder="drop"),
        LogisticRegression(solver="liblinear"),
    )
    model.fit(train[FEATURES], train[TARGET])

    out = Path("models_refus")
    out.mkdir(exist_ok=True)
    joblib.dump(model, out / "model.joblib")
    meta = {"model": "logreg_sans_conso", "mlflow_run_id": None, "decision_threshold": 0.5, "features": FEATURES}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    print("modele candidat sauvegarde dans", out)


if __name__ == "__main__":
    main()
