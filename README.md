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

Prérequis : Python 3.12 et make (Docker sera nécessaire plus tard).

```bash
make setup   # crée le venv et installe les dépendances
make test    # lance les tests
```

Les données seront récupérées et versionnées avec DVC (étape suivante).

## Organisation du dépôt

```
params.yaml        paramètres du projet (source des données, découpage, cible)
requirements.txt   dépendances avec versions fixées
Makefile           commandes du projet
tests/             tests pytest
docs/              cadrage, dictionnaire, décisions
data/              données locales (pas dans git)
```

## Avancement

- [x] Cadrage et structure du projet
- [ ] Ingestion et versionnement des données (DVC), validation, features, découpage temporel
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
