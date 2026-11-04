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

Prérequis : Python 3.12, git, make, Docker et docker compose.

Tout lancer depuis zéro (dans un dépôt git) :

```bash
make all
```

Ce qui revient à :

```bash
make setup        # crée le venv et installe les dépendances
make mlflow       # lance le serveur MLflow (docker compose) sur http://localhost:5000
make data         # télécharge les données UCI avec DVC
make pipeline     # dvc repro : validation, features, entraînement, gate, registre
make up           # construit l'image de l'API et lance tout avec docker compose
```

Autres commandes :

```bash
make down         # arrête les conteneurs
make logs         # logs de l'API
make test         # lance les tests
make demo-rejet   # exemple de données invalides refusées par la validation
make demo-gate-refus  # exemple de modèle refusé par la quality gate
make api          # lance l'API sans Docker sur http://localhost:8000 (doc sur /docs)
make demo-api     # 3 requêtes d'exemple (été, hiver, entrée invalide)
```

## Pipeline de données

Le pipeline est décrit dans `dvc.yaml` et les empreintes de chaque fichier sont dans `dvc.lock`.

1. `data/raw/tetouan.zip.dvc` : import du fichier UCI avec `dvc import-url` (URL + md5)
2. `validate` : lecture du CSV, renommage des colonnes, vérification du schéma (pandera).
   Si une règle n'est pas respectée le pipeline s'arrête. Résultat dans `reports/data_validation.json`.
3. `features` : calcul des features (passé uniquement), du seuil de pic (sur le train) et de la
   cible, puis découpage temporel en `train.csv`, `test.csv`, `production.csv`.
   Statistiques dans `reports/data_stats.json`.
4. `train` : entraînement de trois modèles (baseline de persistance, régression logistique,
   gradient boosting). Les 3 dernières semaines du train servent de validation pour choisir le
   seuil de décision et le meilleur modèle. Chaque modèle est ensuite évalué une seule fois sur
   le test. Tout est enregistré dans MLflow (paramètres, métriques, empreintes des données,
   modèle). Le modèle retenu est sauvegardé dans `models/` et ses métriques dans `reports/metrics.json`.
5. `gate` : quality gate. Le modèle est rechargé et réévalué sur le test, puis il doit passer
   tous les contrôles (techniques, performances, sous-groupe week-end). Sinon le pipeline
   s'arrête avec une erreur. Décision et détail dans `reports/quality_gate.json`, et la décision
   est aussi ajoutée comme tag sur le run MLflow.
6. `register` : si la gate a accepté le modèle, il est enregistré dans le registre MLflow
   (`tetouan-pics-model`) avec ses réglages en tags, et reçoit l'alias `champion`.
   Résultat dans `reports/registry.json`.

## API

L'API FastAPI (`src/app.py`) sert le modèle `champion` du registre. Le contrat (entrées,
contraintes, sortie) est décrit dans `docs/api.md`.

## Docker

`docker-compose.yml` lance le serveur MLflow et l'API. L'image de l'API est construite avec le
`Dockerfile` (python slim, utilisateur non root, healthcheck). Détails et stratégie de mise en
production : `docs/deploiement.md`.

Les données ne sont pas dans git, seulement leurs empreintes.

## Organisation du dépôt

```
params.yaml        paramètres du projet (chemins, découpage, cible)
dvc.yaml           étapes du pipeline
dvc.lock           empreintes des données et du code de chaque étape
requirements.txt   dépendances du projet avec versions fixées
requirements-docker.txt  dépendances minimales de l'image de l'API
Makefile           commandes du projet
src/schema.py      schéma de validation des données
src/validate.py    étape validate
src/features.py    étape features
src/train.py       étape train (+ suivi MLflow)
src/quality_gate.py   étape gate
src/demo_mauvais_modele.py  modèle volontairement mauvais pour la démo de refus
src/register.py    étape register (registre MLflow)
src/app.py         API FastAPI
examples/          requêtes d'exemple pour l'API
Dockerfile         image de l'API
docker-compose.yml serveur MLflow + API
models/            modèle retenu et ses métadonnées (géré par DVC)
tests/             tests pytest (+ tests/data/ : fichier invalide pour la démo)
reports/           rapports générés (validation, statistiques)
docs/              cadrage, dictionnaire, décisions, contrat d'API, déploiement
data/              données (gérées par DVC, pas dans git)
```

## Avancement

- [x] Cadrage et structure du projet
- [x] Ingestion et versionnement des données (DVC), validation, features, découpage temporel
- [x] Entraînement et suivi MLflow
- [x] Quality gate
- [x] API FastAPI et registre de modèles
- [x] Docker
- [ ] CI GitHub Actions
- [ ] Monitoring Prometheus / Grafana
- [ ] Détection de dérive et alertes
- [ ] Feedback, réentraînement, promotion, rollback
- [ ] Rapport final

## Données

Power Consumption of Tetouan City, UCI Machine Learning Repository (licence CC BY 4.0).
Salam, A. & El Hibaoui, A. (2018). Comparison of Machine Learning Algorithms for the Power
Consumption Prediction: Case Study of Tetouan city. IRSEC 2018.
