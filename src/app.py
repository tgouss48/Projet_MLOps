# API de prediction des pics de consommation
# Lancer avec : uvicorn app:app --app-dir src --port 8000
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException
from mlflow import MlflowClient
from pydantic import BaseModel, Field

from features import add_derived

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "tetouan-pics-model")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")


class Mesure(BaseModel):
    # memes plages que le schema de validation des donnees (src/schema.py)
    datetime: datetime
    temperature: float = Field(ge=-5, le=50, description="°C")
    humidity: float = Field(ge=0, le=100, description="%")
    wind_speed: float = Field(ge=0, le=20, description="m/s")
    general_diffuse_flows: float = Field(ge=0, le=1500, description="W/m²")
    diffuse_flows: float = Field(ge=0, le=1500, description="W/m²")
    total_kw: float = Field(gt=0, le=300000, description="consommation totale actuelle")
    lag_10min: float = Field(gt=0, le=300000, description="consommation il y a 10 min")
    lag_1h: float = Field(gt=0, le=300000, description="consommation il y a 1 h")
    lag_24h: float = Field(gt=0, le=300000, description="consommation il y a 24 h")
    mean_1h: float = Field(gt=0, le=300000, description="moyenne sur la derniere heure")

    model_config = {"json_schema_extra": {"example": {
        "datetime": "2017-07-15T20:00:00", "temperature": 31.5, "humidity": 45.0, "wind_speed": 0.8,
        "general_diffuse_flows": 120.0, "diffuse_flows": 90.0, "total_kw": 95000.0,
        "lag_10min": 94000.0, "lag_1h": 90000.0, "lag_24h": 93000.0, "mean_1h": 92500.0}}}


class Prediction(BaseModel):
    prediction_id: str
    datetime: datetime
    peak_probability: float
    alert: bool
    decision_threshold: float
    model_version: str


class Lot(BaseModel):
    mesures: list[Mesure] = Field(min_length=1, max_length=5000)


def load_model():
    mlflow.set_tracking_uri(TRACKING_URI)
    mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@{MODEL_ALIAS}")
    return {
        "model": model,
        "version": str(mv.version),
        "run_id": mv.run_id,
        "threshold": float(mv.tags["decision_threshold"]),
        "features": json.loads(mv.tags["features"]),
        "algo": mv.tags.get("algo"),
    }


state = {}


@asynccontextmanager
async def lifespan(app):
    # le modele est charge une seule fois au demarrage
    # si le registre n'est pas joignable l'API demarre quand meme mais /health renvoie 503
    try:
        state.update(load_model())
    except Exception as e:
        print("impossible de charger le modele :", e)
    yield


app = FastAPI(title="Alerte pics de consommation - Tetouan", version="1.0", lifespan=lifespan)


def predire(mesures):
    if "model" not in state:
        raise HTTPException(503, "modele non charge")
    df = pd.DataFrame([m.model_dump() for m in mesures])
    df["datetime"] = pd.to_datetime(df["datetime"])
    X = add_derived(df)[state["features"]].astype(float)
    proba = state["model"].predict_proba(X)[:, 1]
    return [
        Prediction(
            prediction_id=str(uuid.uuid4()),
            datetime=m.datetime,
            peak_probability=round(float(p), 4),
            alert=bool(p >= state["threshold"]),
            decision_threshold=state["threshold"],
            model_version=state["version"],
        )
        for m, p in zip(mesures, proba)
    ]


@app.get("/health")
def health():
    if "model" not in state:
        raise HTTPException(503, "modele non charge")
    return {"status": "ok", "model_version": state["version"]}


@app.get("/model")
def model_info():
    if "model" not in state:
        raise HTTPException(503, "modele non charge")
    return {"name": MODEL_NAME, "alias": MODEL_ALIAS, "version": state["version"], "algo": state["algo"],
            "mlflow_run_id": state["run_id"], "decision_threshold": state["threshold"],
            "features": state["features"]}


@app.post("/predict", response_model=Prediction)
def predict(mesure: Mesure):
    return predire([mesure])[0]


@app.post("/predict/batch", response_model=list[Prediction])
def predict_batch(lot: Lot):
    return predire(lot.mesures)
