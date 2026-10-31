import numpy as np
import pandas as pd

from features import add_features, add_target, split


def jeu(n=300):
    total = np.arange(n, dtype=float)
    return pd.DataFrame({
        "datetime": pd.date_range("2017-04-30 00:00", periods=n, freq="10min"),
        "temperature": 15.0, "humidity": 70.0, "wind_speed": 0.1,
        "general_diffuse_flows": 0.1, "diffuse_flows": 0.1,
        "zone1_kw": total, "zone2_kw": 0.0, "zone3_kw": 0.0,
    })


def test_lags_utilisent_le_passe():
    df = add_features(jeu())
    assert df["lag_10min"].iloc[10] == df["total_kw"].iloc[9]
    assert df["lag_1h"].iloc[10] == df["total_kw"].iloc[4]


def test_cible_regarde_une_heure_plus_tard():
    df = add_target(add_features(jeu()), threshold=100, horizon=6)
    assert df["target_peak_h1"].iloc[94] == 0   # total a t+1h = 100, pas > 100
    assert df["target_peak_h1"].iloc[95] == 1   # total a t+1h = 101


def test_pas_de_fuite_entre_train_et_test():
    df = add_target(add_features(jeu()), threshold=100, horizon=6)
    p = {"train_start": "2017-01-01", "train_end": "2017-04-30",
         "test_start": "2017-05-01", "test_end": "2017-05-31",
         "production_start": "2017-06-01"}
    train, test, _ = split(df, p)
    # aucune cible du train ne doit tomber en mai
    assert train["target_time"].max() < pd.Timestamp("2017-05-01")
    assert train["datetime"].max() < test["datetime"].min()
