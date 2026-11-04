import json
import os

import mlflow
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from mlflow import MlflowClient
from sklearn.ensemble import HistGradientBoostingClassifier

from features import FEATURES, add_derived

NOM = "modele-test"


def mesures(n=50, seed=0):
    rng = np.random.default_rng(seed)
    total = rng.uniform(50000, 110000, n)
    return pd.DataFrame({
        "datetime": pd.date_range("2017-07-01", periods=n, freq="10min"),
        "temperature": rng.uniform(10, 35, n), "humidity": rng.uniform(30, 90, n),
        "wind_speed": rng.uniform(0, 5, n), "general_diffuse_flows": rng.uniform(0, 800, n),
        "diffuse_flows": rng.uniform(0, 500, n), "total_kw": total,
        "lag_10min": total * 0.99, "lag_1h": total * 0.95, "lag_24h": total * 1.01, "mean_1h": total * 0.97,
    })


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # petit registre MLflow temporaire avec un modele entraine sur des donnees fictives
    tmp = tmp_path_factory.mktemp("mlflow")
    uri = f"sqlite:///{tmp}/mlflow.db"
    mlflow.set_tracking_uri(uri)
    exp = mlflow.create_experiment("test", artifact_location=str(tmp / "artifacts"))

    df = add_derived(mesures(500, seed=1))
    y = (df["total_kw"] > 90000).astype(int)
    model = HistGradientBoostingClassifier(max_iter=20).fit(df[FEATURES], y)

    with mlflow.start_run(experiment_id=exp) as run:
        mlflow.sklearn.log_model(model, "model")
    mv = mlflow.register_model(f"runs:/{run.info.run_id}/model", NOM)
    c = MlflowClient()
    c.set_model_version_tag(NOM, mv.version, "decision_threshold", "0.3")
    c.set_model_version_tag(NOM, mv.version, "features", json.dumps(FEATURES))
    c.set_registered_model_alias(NOM, "champion", mv.version)

    os.environ.update({"MLFLOW_TRACKING_URI": uri, "MODEL_NAME": NOM, "MODEL_ALIAS": "champion"})
    import app as api
    api.TRACKING_URI, api.MODEL_NAME = uri, NOM
    with TestClient(api.app) as cl:
        cl.model = model
        yield cl


def payload(row):
    d = row.to_dict()
    d["datetime"] = row["datetime"].isoformat()
    return d


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["model_version"] == "1"


def test_infos_modele(client):
    r = client.get("/model").json()
    assert r["decision_threshold"] == 0.3 and r["features"] == FEATURES


def test_prediction_ok(client):
    r = client.post("/predict", json=payload(mesures(1).iloc[0]))
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["peak_probability"] <= 1
    assert body["alert"] == (body["peak_probability"] >= 0.3)
    assert body["model_version"] == "1"


def test_meme_resultat_que_le_pipeline(client):
    # l'API doit calculer les features exactement comme a l'entrainement
    df = mesures(30, seed=5)
    r = client.post("/predict/batch", json={"mesures": [payload(row) for _, row in df.iterrows()]})
    api_proba = np.array([p["peak_probability"] for p in r.json()])
    direct = client.model.predict_proba(add_derived(df)[FEATURES])[:, 1]
    assert np.allclose(api_proba, direct.round(4), atol=1e-4)


def test_temperature_impossible_refusee(client):
    d = payload(mesures(1).iloc[0])
    d["temperature"] = -999
    r = client.post("/predict", json=d)
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "temperature"]


def test_champ_manquant_refuse(client):
    d = payload(mesures(1).iloc[0])
    del d["lag_1h"]
    assert client.post("/predict", json=d).status_code == 422


def test_lot_vide_refuse(client):
    assert client.post("/predict/batch", json={"mesures": []}).status_code == 422
