# Simulation de trafic sur l'API a partir des vraies donnees, puis etat des alertes Prometheus
# Lancer avec : python scripts/simulate_traffic.py <scenario> [--duree 150] [--rps 10]
# Scenarios :
#   stable  : mesures de mai (periode de test, proche de l'entrainement)
#   capteur : mesures de mai mais 30 % avec un capteur de temperature en panne (-999)
#   ete     : mesures de juillet (chaleur, beaucoup de pics, jamais vu a l'entrainement)
import argparse
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

API = "http://localhost:8000"
PROMETHEUS = "http://localhost:9090"
CHAMPS = ["datetime", "temperature", "humidity", "wind_speed", "general_diffuse_flows", "diffuse_flows",
          "total_kw", "lag_10min", "lag_1h", "lag_24h", "mean_1h"]

SCENARIOS = {
    "stable": {"fichier": "test.csv", "debut": "2017-05-01", "panne": 0.0},
    "capteur": {"fichier": "test.csv", "debut": "2017-05-01", "panne": 0.3},
    "ete": {"fichier": "production.csv", "debut": "2017-07-10", "panne": 0.0},
}


def post(route, data):
    req = urllib.request.Request(API + route, data=json.dumps(data).encode(), method="POST")
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def prom(chemin):
    with urllib.request.urlopen(PROMETHEUS + chemin, timeout=5) as r:
        return json.loads(r.read())["data"]


def valeur(requete):
    res = prom("/api/v1/query?query=" + urllib.parse.quote(requete))["result"]
    return round(float(res[0]["value"][1]), 4) if res else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("--duree", type=int, default=150, help="secondes")
    parser.add_argument("--rps", type=float, default=10, help="requetes par seconde")
    args = parser.parse_args()
    sc = SCENARIOS[args.scenario]
    random.seed(0)

    df = pd.read_csv(Path("data/processed") / sc["fichier"], parse_dates=["datetime"])
    df = df[df["datetime"] >= sc["debut"]].reset_index(drop=True)
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"scenario {args.scenario} : {args.duree} s a {args.rps} req/s a partir du {sc['debut']}")
    codes, alertes, i = {}, 0, 0
    fin = time.time() + args.duree
    while time.time() < fin and i < len(df):
        mesure = df.loc[i, CHAMPS].to_dict()
        if random.random() < sc["panne"]:
            mesure["temperature"] = -999.0
        code, rep = post("/predict", mesure)
        codes[code] = codes.get(code, 0) + 1
        alertes += int(bool(rep and rep["alert"]))
        i += 1
        if i % 200 == 0:
            print(f"  {i} requetes, codes {codes}")
        time.sleep(1 / args.rps)

    time.sleep(10)  # laisser Prometheus collecter et evaluer les regles
    actives = [a for a in prom("/api/v1/alerts")["alerts"]]
    rapport = {
        "scenario": args.scenario,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requetes": i,
        "codes_http": {str(k): v for k, v in codes.items()},
        "taux_alertes_modele": round(alertes / max(1, codes.get(200, 1)), 4),
        "metriques_prometheus": {
            "latence_p95_s": valeur('histogram_quantile(0.95, sum by (le) '
                                    '(rate(api_request_duration_seconds_bucket{route="/predict"}[1m])))'),
            "taux_422_1m": valeur('(sum(rate(api_requests_total{status="422"}[1m])) or vector(0)) / '
                                  'sum(rate(api_requests_total{route="/predict"}[1m]))'),
            "taux_alertes_5m": valeur('sum(rate(predictions_total{alert="true"}[5m])) / '
                                      'sum(rate(predictions_total[5m]))'),
            "temperature_moyenne_5m": valeur("sum(rate(input_temperature_celsius_sum[5m])) / "
                                             "sum(rate(input_temperature_celsius_count[5m]))"),
        },
        "alertes_prometheus": [
            {"alerte": a["labels"]["alertname"], "etat": a["state"], "decision": a["annotations"].get("decision")}
            for a in actives
        ],
    }
    out = Path(f"reports/monitoring_{args.scenario}.json")
    out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))

    print(json.dumps(rapport["metriques_prometheus"], indent=2))
    if not actives:
        print("aucune alerte Prometheus")
    for a in rapport["alertes_prometheus"]:
        print(f"ALERTE {a['alerte']} ({a['etat']}) -> {a['decision']}")
    print("rapport :", out)


if __name__ == "__main__":
    main()
