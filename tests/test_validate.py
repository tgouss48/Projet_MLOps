import pandas as pd

from validate import validate


def petit_jeu(n=20):
    return pd.DataFrame({
        "datetime": pd.date_range("2017-01-01", periods=n, freq="10min"),
        "temperature": 15.0,
        "humidity": 70.0,
        "wind_speed": 0.08,
        "general_diffuse_flows": 0.05,
        "diffuse_flows": 0.1,
        "zone1_kw": 30000.0,
        "zone2_kw": 18000.0,
        "zone3_kw": 20000.0,
    })


def test_donnees_correctes_acceptees():
    ok, errors = validate(petit_jeu())
    assert ok and errors == []


def test_capteur_en_panne_rejete():
    df = petit_jeu()
    df.loc[3, "temperature"] = -999.0
    ok, errors = validate(df)
    assert not ok
    assert errors[0]["column"] == "temperature"


def test_humidite_impossible_rejetee():
    df = petit_jeu()
    df.loc[5, "humidity"] = 150.0
    assert not validate(df)[0]


def test_consommation_nulle_rejetee():
    df = petit_jeu()
    df.loc[0, "zone2_kw"] = 0.0
    assert not validate(df)[0]


def test_trou_dans_les_mesures_rejete():
    df = petit_jeu().drop(index=7)
    assert not validate(df)[0]


def test_colonne_manquante_rejetee():
    assert not validate(petit_jeu().drop(columns="wind_speed"))[0]
