# Enregistrement du modele accepte dans le registre MLflow
# Lancer avec : python src/register.py
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import yaml
from mlflow import MlflowClient


def main():
    params = yaml.safe_load(open("params.yaml"))["mlflow"]
    meta = json.load(open("models/metadata.json"))
    gate = json.load(open("reports/quality_gate.json"))

    # securite : on n'enregistre jamais un modele refuse par la quality gate
    if gate["decision"] != "ACCEPTE" or gate["mlflow_run_id"] != meta["mlflow_run_id"]:
        print("modele non accepte par la quality gate, pas d'enregistrement")
        sys.exit(1)

    mlflow.set_tracking_uri(params["tracking_uri"])
    client = MlflowClient()
    name = params["model_name"]

    mv = mlflow.register_model(f"runs:/{meta['mlflow_run_id']}/model", name)
    tags = {
        "decision_threshold": meta["decision_threshold"],
        "peak_threshold_kw": meta["peak_threshold_kw"],
        "features": json.dumps(meta["features"]),
        "train_md5": meta["train_md5"],
        "algo": meta["model"],
        "quality_gate": gate["decision"],
    }
    for k, v in tags.items():
        client.set_model_version_tag(name, mv.version, k, str(v))

    # pour l'instant chaque modele accepte devient le champion (la comparaison
    # champion / challenger sera ajoutee avec la gestion du cycle de vie)
    client.set_registered_model_alias(name, "champion", mv.version)

    info = {"model_name": name, "version": mv.version, "alias": "champion",
            "mlflow_run_id": meta["mlflow_run_id"],
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    Path("reports/registry.json").write_text(json.dumps(info, indent=2))
    print(f"{name} version {mv.version} enregistree, alias champion")


if __name__ == "__main__":
    main()
