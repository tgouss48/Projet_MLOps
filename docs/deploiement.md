# Packaging et mise en production

## Ce qui tourne

`docker compose up` lance deux conteneurs :

| Service | Image | Port | Rôle |
|---|---|---|---|
| mlflow | ghcr.io/mlflow/mlflow:v2.19.0 | 5000 | suivi des expériences + registre de modèles + stockage des modèles |
| api | tetouan-api:1.0 (notre Dockerfile) | 8000 | API de prédiction |

Les données de MLflow (base SQLite et modèles) sont dans le volume Docker `mlflow_data`, elles
restent après un `docker compose down` (mais pas après `docker compose down -v`).

Le pipeline (`make pipeline`) tourne sur la machine et envoie les runs et les modèles au
serveur MLflow sur http://localhost:5000. L'API, elle, va chercher le modèle `champion` sur
http://mlflow:5000 (réseau interne de docker compose).

```
 machine                         docker compose
 ───────                         ──────────────────────────────────────
 make pipeline  ── runs, modèles ──►  mlflow (5000) ◄── charge champion ── api (8000)
                                      volume mlflow_data                     ▲
                                                                             │
                                                     client (dispatching) ───┘
```

## Image de l'API

- base `python:3.12-slim`, dépendances figées dans `requirements-docker.txt` (seulement ce qu'il
  faut pour servir : pas de dvc, pytest, ni mlflow complet)
- seulement 3 fichiers de code copiés (`app.py`, `features.py`, `schema.py`), le reste est exclu
  par `.dockerignore`
- utilisateur non root (`appuser`)
- healthcheck sur `/health` toutes les 15 s (en python car curl n'est pas dans l'image slim)
- le modèle n'est pas dans l'image : il est chargé depuis le registre au démarrage

## Pourquoi le modèle n'est pas dans l'image

On sépare la version du code (l'image) et la version du modèle (le registre) :
- changer de modèle = déplacer l'alias `champion` puis redémarrer l'API, sans reconstruire l'image
- revenir en arrière (rollback) = remettre l'alias sur l'ancienne version
- la version servie est visible dans chaque réponse (`model_version`) et sur `/model`

Inconvénient : l'API dépend du serveur MLflow au démarrage. Si le registre n'est pas
joignable, l'API démarre quand même mais `/health` répond 503, le conteneur est marqué
unhealthy et aucune prédiction n'est faite (pas de modèle au hasard).

## Stratégie de mise en production

1. un nouveau modèle est entraîné par le pipeline
2. il doit passer la quality gate, sinon il n'est pas enregistré
3. il est enregistré dans le registre
4. il devient `champion` (pour l'instant automatiquement ; la comparaison avec l'ancien
   champion est ajoutée à l'étape cycle de vie)
5. redémarrage de l'API (`docker compose restart api`), qui charge le nouveau champion
6. vérification : `/health` et `/model` donnent la nouvelle version

Le code de l'API, lui, passe par la CI avant d'être construit en image : lint, tests, pipeline
complet avec quality gate, test de fumée sur la stack docker. Si tout passe sur la branche
principale, l'image est publiée sur GitHub Container Registry avec le hash court du commit
comme tag (et `latest`). On sait donc toujours quel code tourne dans quelle image.

## Limites

- un seul conteneur API, pas de répartition de charge (hors périmètre du projet)
- SQLite pour MLflow : suffisant pour un projet local, pas pour plusieurs utilisateurs en même temps
- pas d'authentification sur l'API ni sur MLflow
