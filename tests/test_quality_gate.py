import numpy as np
import pandas as pd

from features import FEATURES
from quality_gate import run_checks

GATE = {"min_recall": 0.85, "min_precision": 0.5, "min_pr_auc": 0.8,
        "min_recall_weekend": 0.75, "max_latency_ms": 50}


class FauxModele:
    # renvoie une proba proche de la vraie cible, avec un taux d'erreur choisi
    def __init__(self, y, erreurs=0.0, seed=0):
        rng = np.random.default_rng(seed)
        flip = rng.random(len(y)) < erreurs
        self.p = np.where(flip, 1 - y, y) * 0.9 + 0.05

    def predict_proba(self, X):
        p = self.p[: len(X)] if len(X) == len(self.p) else np.full(len(X), 0.5)
        return np.column_stack([1 - p, p])


def jeu_test(n=400):
    rng = np.random.default_rng(1)
    df = pd.DataFrame(rng.random((n, len(FEATURES))), columns=FEATURES)
    df["is_weekend"] = (np.arange(n) % 7 >= 5).astype(int)
    df["total_kw"] = 80000.0
    df["target_peak_h1"] = (np.arange(n) % 4 == 0).astype(int)
    return df


def meta(features=FEATURES):
    return {"features": features, "decision_threshold": 0.5}


def test_bon_modele_accepte():
    t = jeu_test()
    checks = run_checks(FauxModele(t["target_peak_h1"].to_numpy()), meta(), t, 92000, GATE, 5, 1)
    assert all(c["ok"] for c in checks)


def test_modele_qui_se_trompe_refuse():
    t = jeu_test()
    checks = run_checks(FauxModele(t["target_peak_h1"].to_numpy(), erreurs=0.4), meta(), t, 92000, GATE, 5, 1)
    refus = [c["controle"] for c in checks if not c["ok"]]
    assert "rappel" in refus


def test_mauvaises_features_refuse():
    t = jeu_test()
    checks = run_checks(FauxModele(t["target_peak_h1"].to_numpy()), meta(FEATURES[:-1]), t, 92000, GATE, 5, 1)
    assert checks[0]["controle"] == "features attendues" and not checks[0]["ok"]
