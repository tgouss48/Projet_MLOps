# Analyse de derive semaine par semaine sur la periode de production
# Lancer avec : python src/drift.py
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import recall_score

from features import FEATURES
from train import TARGET

METEO = ["temperature", "humidity", "wind_speed", "general_diffuse_flows", "diffuse_flows"]


def psi(ref, cur, bins=10):
    # Population Stability Index : 0 = meme distribution, > 0.25 = changement important
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.clip(r, 1e-4, None), np.clip(c, 1e-4, None)
    return float(np.sum((c - r) * np.log(c / r)))


def hors_domaine(valeurs, bas, haut):
    # part des valeurs que le modele n'a (presque) jamais vues a l'entrainement
    return float(((valeurs < bas) | (valeurs > haut)).mean())


def statut(ind, s):
    if ind["hors_domaine_conso"] > s["hors_domaine_derive"] or (
        ind["psi_conso"] > s["psi_derive"] and ind["hors_domaine_conso"] > s["hors_domaine_attention"]
    ):
        return "DERIVE"
    if (ind["hors_domaine_conso"] > s["hors_domaine_attention"] or ind["psi_conso"] > s["psi_attention"]
            or ind["hors_domaine_temp"] > s["temp_hors_domaine_attention"]):
        return "ATTENTION"
    return "STABLE"


def analyse(ref, cur, s, model=None, seuil=None, cout_fn=5, cout_fp=1):
    bornes = {c: (ref[c].quantile(0.01), ref[c].quantile(0.99)) for c in ["temperature", "total_kw"]}
    semaines, derive_consecutives, decision = [], 0, None

    for debut, g in cur.groupby(cur["datetime"].dt.to_period(s["frequence"]).dt.start_time):
        ind = {
            "hors_domaine_conso": round(hors_domaine(g["total_kw"], *bornes["total_kw"]), 3),
            "psi_conso": round(psi(ref["total_kw"], g["total_kw"]), 3),
            "hors_domaine_temp": round(hors_domaine(g["temperature"], *bornes["temperature"]), 3),
            "psi_meteo": {c: round(psi(ref[c], g[c]), 2) for c in METEO},
        }
        ligne = {"semaine": str(debut.date()), "n": len(g), **ind, "statut": statut(ind, s)}

        # performance reelle (connue apres coup) : sert a verifier que les indicateurs sont utiles
        if model is not None:
            alerte = model.predict_proba(g[FEATURES])[:, 1] >= seuil
            y = g[TARGET].to_numpy()
            ligne["taux_alertes"] = round(float(alerte.mean()), 3)
            ligne["taux_pics_reels"] = round(float(y.mean()), 3)
            # pas de rappel s'il n'y a eu aucun pic dans la semaine
            ligne["rappel_reel"] = round(recall_score(y, alerte), 3) if y.sum() > 0 else None
            fn, fp = int(((~alerte) & (y == 1)).sum()), int((alerte & (y == 0)).sum())
            ligne["cout_par_jour"] = round((cout_fn * fn + cout_fp * fp) / (len(g) / 144), 1)

        derive_consecutives = derive_consecutives + 1 if ligne["statut"] == "DERIVE" else 0
        if decision is None and derive_consecutives >= s["semaines_avant_reentrainement"]:
            fin = g["datetime"].max()
            decision = {"semaine": ligne["semaine"], "donnees_disponibles_jusqu_au": str(fin.date()),
                        "action": "REENTRAINER"}
        semaines.append(ligne)

    return semaines, decision


def tableau(semaines):
    lignes = ["| Semaine | Statut | Hors domaine conso | PSI conso | Hors domaine temp | Alertes | Pics réels "
              "| Rappel réel | Coût / jour |", "|---|---|---|---|---|---|---|---|---|"]
    for w in semaines:
        lignes.append(f"| {w['semaine']} | {w['statut']} | {w['hors_domaine_conso']:.0%} | {w['psi_conso']:.2f} "
                      f"| {w['hors_domaine_temp']:.0%} | {w.get('taux_alertes', 0):.0%} "
                      f"| {w.get('taux_pics_reels', 0):.0%} "
                      f"| {'-' if w.get('rappel_reel') is None else format(w['rappel_reel'], '.2f')} "
                      f"| {w.get('cout_par_jour', 0):.0f} |")
    return "\n".join(lignes)


def main():
    params = yaml.safe_load(open("params.yaml"))
    s, p = params["drift"], params["train"]
    d = Path(params["data"]["processed_dir"])
    ref = pd.read_csv(d / "train.csv", parse_dates=["datetime"])
    cur = pd.concat([pd.read_csv(d / f"{n}.csv", parse_dates=["datetime"]) for n in ["test", "production"]])

    model = joblib.load("models/model.joblib")
    meta = json.load(open("models/metadata.json"))
    semaines, decision = analyse(ref, cur, s, model, meta["decision_threshold"], p["cost_fn"], p["cost_fp"])

    compte = {k: sum(w["statut"] == k for w in semaines) for k in ["STABLE", "ATTENTION", "DERIVE"]}
    rapport = {"reference": "train (janvier-avril 2017)", "modele": meta["model"], "seuils": s,
               "resume": compte, "decision": decision, "semaines": semaines}
    Path("reports/drift.json").write_text(json.dumps(rapport, indent=2, ensure_ascii=False))

    md = ["# Analyse de dérive par semaine", "", f"Référence : {rapport['reference']}. "
          f"Semaines : {compte['STABLE']} stables, {compte['ATTENTION']} attention, {compte['DERIVE']} dérive.", ""]
    if decision:
        md += [f"**Décision : {decision['action']}** à la fin de la semaine du {decision['semaine']} "
               f"({s['semaines_avant_reentrainement']} semaines DERIVE de suite), avec les données disponibles "
               f"jusqu'au {decision['donnees_disponibles_jusqu_au']}.", ""]
    md += [tableau(semaines), "", "Rappel réel et coût : calculés après coup avec la vraie consommation, "
           "pour vérifier que les indicateurs de dérive suivent bien la dégradation du modèle."]
    Path("reports/drift.md").write_text("\n".join(md) + "\n")

    print(f"semaines : {compte}")
    print("decision :", decision)


if __name__ == "__main__":
    main()
