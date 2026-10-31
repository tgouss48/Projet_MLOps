# Prédiction des pics de consommation électrique - Tétouan

Projet MLOps réalisé dans le cadre du module MLOps.

L'objectif est de prédire toutes les 10 minutes si la consommation électrique totale de la ville
de Tétouan va dépasser un seuil de pic dans l'heure qui suit. Le but est d'aider le centre de
dispatching à anticiper (activer une réserve, préparer un effacement) au lieu de subir le pic.

Le modèle reste volontairement simple. On s'est surtout concentrés sur le cycle de vie :
traçabilité des données, quality gate, service versionné, monitoring, dérive, feedback et rollback.

Documents :
- cadrage métier et protocole : `docs/01_cadrage.md`
- dictionnaire de données : `docs/data_dictionary.md`
- journal des décisions : `docs/decision_log.md`

## Installation

Prérequis : Python 3.12, git et make (Docker sera nécessaire plus tard).

```bash
make setup        # crée le venv et installe les dépendances
make data         # télécharge les données UCI avec DVC
make pipeline     # dvc repro : validation des données puis features et découpage
make test         # lance les tests
make demo-rejet   # exemple de données invalides refusées par la validation
```

## Pipeline de données

Le pipeline est décrit dans `dvc.yaml` et les empreintes de chaque fichier sont dans `dvc.lock`.

1. `data/raw/tetouan.zip.dvc` : import du fichier UCI avec `dvc import-url` (URL + md5)
2. `validate` : lecture du CSV, renommage des colonnes, vérification du schéma (pandera).
   Si une règle n'est pas respectée le pipeline s'arrête. Résultat dans `reports/data_validation.json`.
3. `features` : calcul des features (passé uniquement), du seuil de pic (sur le train) et de la
   cible, puis découpage temporel en `train.csv`, `test.csv`, `production.csv`.
   Statistiques dans `reports/data_stats.json`.

Les données ne sont pas dans git, seulement leurs empreintes.

## Organisation du dépôt

```
params.yaml        paramètres du projet (chemins, découpage, cible)
dvc.yaml           étapes du pipeline
dvc.lock           empreintes des données et du code de chaque étape
requirements.txt   dépendances avec versions fixées
Makefile           commandes du projet
src/schema.py      schéma de validation des données
src/validate.py    étape validate
src/features.py    étape features
tests/             tests pytest (+ tests/data/ : fichier invalide pour la démo)
reports/           rapports générés (validation, statistiques)
docs/              cadrage, dictionnaire, décisions
data/              données (gérées par DVC, pas dans git)
```

## Avancement

- [x] Cadrage et structure du projet
- [x] Ingestion et versionnement des données (DVC), validation, features, découpage temporel
- [ ] Entraînement et suivi MLflow
- [ ] Quality gate
- [ ] API FastAPI
- [ ] Docker
- [ ] CI GitHub Actions
- [ ] Monitoring Prometheus / Grafana
- [ ] Détection de dérive et alertes
- [ ] Feedback, réentraînement, promotion, rollback
- [ ] Rapport final

## Données

Power Consumption of Tetouan City, UCI Machine Learning Repository (licence CC BY 4.0).
Salam, A. & El Hibaoui, A. (2018). Comparison of Machine Learning Algorithms for the Power
Consumption Prediction: Case Study of Tetouan city. IRSEC 2018.
