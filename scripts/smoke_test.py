# Test de fumee : verifie que l'API deployee (docker compose) repond correctement
# Lancer avec : python scripts/smoke_test.py [url]   (par defaut http://localhost:8000)
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def appel(route, data=None):
    req = urllib.request.Request(URL + route, method="POST" if data is not None else "GET")
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def exemple(nom):
    return json.loads(Path(f"examples/{nom}.json").read_text())


erreurs = []


def verifier(nom, condition):
    print(f"[{'OK' if condition else 'KO'}] {nom}")
    if not condition:
        erreurs.append(nom)


code, body = appel("/health")
verifier("GET /health -> 200", code == 200)

code, info = appel("/model")
verifier(f"GET /model -> version {info.get('version')} ({info.get('algo')})", code == 200)

code, body = appel("/predict", exemple("mesure_ete"))
verifier(f"soir d'ete -> alerte (proba {body.get('peak_probability')})", code == 200 and body["alert"] is True)

code, body = appel("/predict", exemple("mesure_hiver"))
verifier(f"nuit d'hiver -> pas d'alerte (proba {body.get('peak_probability')})", code == 200 and body["alert"] is False)

code, body = appel("/predict", exemple("mesure_invalide"))
verifier("entree invalide -> 422", code == 422)

# un lot de vraies mesures de la periode de production
prod = Path("data/processed/production.csv")
if prod.exists():
    df = pd.read_csv(prod, nrows=500)
    champs = list(exemple("mesure_ete").keys())
    lot = {"mesures": df[champs].to_dict("records")}
    code, body = appel("/predict/batch", lot)
    verifier(f"lot de {len(df)} mesures reelles -> {len(body) if code == 200 else 0} predictions",
             code == 200 and len(body) == len(df))

if erreurs:
    print(len(erreurs), "verification(s) en echec")
    sys.exit(1)
print("API OK")
