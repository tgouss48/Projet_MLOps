# Creation des features, de la cible et decoupage temporel
# Lancer avec : python src/features.py
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from schema import WEATHER_COLS, ZONE_COLS

FEATURES = WEATHER_COLS + [
    "hour_sin", "hour_cos", "dayofweek", "is_weekend",
    "total_kw", "lag_10min", "lag_1h", "lag_24h", "mean_1h", "diff_1h",
]


def add_derived(df):
    # features calculees a partir de la date et des valeurs deja presentes
    # (utilisee aussi par l'API pour avoir exactement le meme calcul qu'a l'entrainement)
    df = df.copy()
    hour = df["datetime"].dt.hour + df["datetime"].dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["dayofweek"] = df["datetime"].dt.dayofweek
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["diff_1h"] = df["total_kw"] - df["lag_1h"]
    return df


def add_features(df):
    # uniquement des infos du passe ou du present
    df = df.sort_values("datetime").copy()
    df["total_kw"] = df[ZONE_COLS].sum(axis=1)
    df["lag_10min"] = df["total_kw"].shift(1)
    df["lag_1h"] = df["total_kw"].shift(6)
    df["lag_24h"] = df["total_kw"].shift(144)
    df["mean_1h"] = df["total_kw"].rolling(6).mean()
    return add_derived(df)


def add_target(df, threshold, horizon):
    df = df.copy()
    df["target_time"] = df["datetime"] + pd.Timedelta(minutes=10 * horizon)
    df["future_kw"] = df["total_kw"].shift(-horizon)
    df["target_peak_h1"] = (df["future_kw"] > threshold).astype(int)
    return df


def split(df, p):
    # une ligne n'est gardee que si sa cible tombe dans la meme periode (pas de fuite)
    def periode(start, end):
        end = pd.Timestamp(end) + pd.Timedelta(days=1)
        m = (df["datetime"] >= start) & (df["target_time"] < end)
        return df[m]

    train = periode(p["train_start"], p["train_end"])
    test = periode(p["test_start"], p["test_end"])
    prod = periode(p["production_start"], "2100-01-01")
    return train, test, prod


def main():
    params = yaml.safe_load(open("params.yaml"))
    p, t = params["protocol"], params["target"]
    out = Path(params["data"]["processed_dir"])
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(params["data"]["clean_csv"], parse_dates=["datetime"])
    df = add_features(df)

    # seuil de pic calcule seulement sur la periode d'entrainement
    fin_train = pd.Timestamp(p["train_end"]) + pd.Timedelta(days=1)
    train_mask = (df["datetime"] >= p["train_start"]) & (df["datetime"] < fin_train)
    threshold = float(df.loc[train_mask, "total_kw"].quantile(t["peak_quantile"]))

    df = add_target(df, threshold, t["horizon_steps"])
    df = df.dropna(subset=FEATURES + ["future_kw"])

    cols = ["datetime"] + FEATURES + ["target_peak_h1"]
    stats = {"peak_threshold_kw": round(threshold, 2)}
    for name, part in zip(["train", "test", "production"], split(df, p)):
        part[cols].to_csv(out / f"{name}.csv", index=False)
        stats[name] = {
            "n_rows": len(part),
            "start": str(part["datetime"].min()),
            "end": str(part["datetime"].max()),
            "peak_rate": round(float(part["target_peak_h1"].mean()), 4),
        }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/data_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
