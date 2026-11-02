import numpy as np
import pandas as pd

from train import Persistance, best_threshold, cost, evaluate


def test_cout_penalise_plus_les_pics_rates():
    y = np.array([1, 1, 0, 0])
    un_pic_rate = np.array([0, 1, 0, 0])
    une_fausse_alerte = np.array([1, 1, 1, 0])
    assert cost(y, un_pic_rate, 5, 1) == 5
    assert cost(y, une_fausse_alerte, 5, 1) == 1


def test_seuil_baisse_quand_les_pics_rates_coutent_cher():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    proba = np.clip(y * 0.4 + rng.random(500) * 0.6, 0, 1)
    assert best_threshold(y, proba, 10, 1) <= best_threshold(y, proba, 1, 10)


def test_persistance():
    X = pd.DataFrame({"total_kw": [80000.0, 95000.0]})
    proba = Persistance(peak_kw=92000).predict_proba(X)[:, 1]
    assert list(proba) == [0.0, 1.0]


def test_evaluate_modele_parfait():
    y = np.array([0, 1, 0, 1])
    m = evaluate(y, np.array([0.1, 0.9, 0.2, 0.8]), 0.5, 5, 1)
    assert m["recall"] == 1 and m["precision"] == 1 and m["cost"] == 0
