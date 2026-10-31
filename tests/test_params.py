from pathlib import Path

import yaml

PARAMS = Path(__file__).resolve().parents[1] / "params.yaml"


def load_params():
    with open(PARAMS, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_periodes_sans_chevauchement():
    p = load_params()["protocol"]
    assert p["train_start"] <= p["train_end"] < p["test_start"] <= p["test_end"] < p["production_start"]


def test_cible():
    t = load_params()["target"]
    assert t["horizon_steps"] > 0
    assert 0 < t["peak_quantile"] < 1
