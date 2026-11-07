# Ecrit un resume en markdown des rapports (affiche dans la page de la CI GitHub)
import json
from pathlib import Path


def lire(nom):
    p = Path("reports") / nom
    return json.loads(p.read_text()) if p.exists() else None


stats = lire("data_stats.json")
metrics = lire("metrics.json")
gate = lire("quality_gate.json")
reg = lire("registry.json")
drift = lire("drift.json")

print("## Resultat du pipeline\n")
if stats:
    print(f"Seuil de pic : {stats['peak_threshold_kw']} kW\n")
    print("| Periode | Lignes | Taux de pics |\n|---|---|---|")
    for k in ("train", "test", "production"):
        print(f"| {k} | {stats[k]['n_rows']} | {stats[k]['peak_rate']:.1%} |")
if metrics:
    t, b = metrics["test"], metrics["baseline_test"]
    print(f"\nModele retenu : **{metrics['best_model']}** (seuil de decision {metrics['decision_threshold']})\n")
    print("| | Rappel | Precision | PR-AUC | Cout |\n|---|---|---|---|---|")
    print(f"| modele | {t['recall']} | {t['precision']} | {t['pr_auc']} | {t['cost']} |")
    print(f"| persistance | {b['recall']} | {b['precision']} | {b['pr_auc']} | {b['cost']} |")
if gate:
    print(f"\n### Quality gate : {gate['decision']}\n")
    print("| Controle | Valeur | Seuil | |\n|---|---|---|---|")
    for c in gate["controles"]:
        print(f"| {c['controle']} | {c['valeur']} | {c['seuil']} | {'OK' if c['ok'] else 'KO'} |")
if reg:
    print(f"\nRegistre : {reg['model_name']} version {reg['version']} -> alias {reg['alias']}")
if drift:
    r = drift["resume"]
    print(f"\nDerive : {r['STABLE']} semaines stables, {r['ATTENTION']} attention, {r['DERIVE']} derive")
    if drift["decision"]:
        print(f"Decision : {drift['decision']['action']} (semaine du {drift['decision']['semaine']})")
