import numpy as np
import pandas as pd

from drift import analyse, hors_domaine, psi, statut

SEUILS = {"frequence": "W", "hors_domaine_attention": 0.10, "hors_domaine_derive": 0.20,
          "psi_attention": 0.5, "psi_derive": 1.0, "temp_hors_domaine_attention": 0.30,
          "semaines_avant_reentrainement": 2}


def test_psi_meme_distribution_proche_de_zero():
    rng = np.random.default_rng(0)
    assert psi(rng.normal(0, 1, 5000), rng.normal(0, 1, 5000)) < 0.05


def test_psi_distribution_decalee_eleve():
    rng = np.random.default_rng(0)
    assert psi(rng.normal(0, 1, 5000), rng.normal(2, 1, 5000)) > 1


def test_hors_domaine():
    assert hors_domaine(pd.Series([1, 5, 10, 20]), 2, 15) == 0.5


def test_statuts():
    base = {"hors_domaine_conso": 0.02, "psi_conso": 0.1, "hors_domaine_temp": 0.0}
    assert statut(base, SEUILS) == "STABLE"
    assert statut({**base, "hors_domaine_temp": 0.5}, SEUILS) == "ATTENTION"
    assert statut({**base, "hors_domaine_conso": 0.25}, SEUILS) == "DERIVE"
    # psi eleve mais valeurs dans le domaine connu (cas de decembre) : pas de derive
    assert statut({**base, "psi_conso": 1.2}, SEUILS) == "ATTENTION"


def semaines(conso_par_semaine):
    rng = np.random.default_rng(1)
    parts = []
    for i, centre in enumerate(conso_par_semaine):
        dates = pd.date_range("2017-07-03", periods=1008, freq="10min") + pd.Timedelta(weeks=i)
        parts.append(pd.DataFrame({"datetime": dates, "total_kw": rng.normal(centre, 3000, 1008),
                                   "temperature": rng.normal(15, 3, 1008), "humidity": 70.0, "wind_speed": 1.0,
                                   "general_diffuse_flows": 100.0, "diffuse_flows": 50.0}))
    return pd.concat(parts, ignore_index=True)


def test_reentrainement_apres_deux_semaines_de_derive():
    ref = semaines([70000] * 4)
    cur = semaines([70000, 100000, 100000, 100000])
    resultat, decision = analyse(ref, cur, SEUILS)
    assert [w["statut"] for w in resultat] == ["STABLE", "DERIVE", "DERIVE", "DERIVE"]
    assert decision["action"] == "REENTRAINER" and decision["semaine"] == resultat[2]["semaine"]


def test_pas_de_decision_si_derive_isolee():
    _, decision = analyse(semaines([70000] * 4), semaines([70000, 100000, 70000, 70000]), SEUILS)
    assert decision is None
