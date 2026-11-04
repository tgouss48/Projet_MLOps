# Contrat de l'API

L'API charge au démarrage le modèle qui a l'alias `champion` dans le registre MLflow
(`tetouan-pics-model`). Le seuil de décision et la liste des features sont lus dans les tags de
cette version, donc l'API utilise toujours les réglages du modèle qu'elle sert.

Lancement : `make api` puis documentation interactive sur http://localhost:8000/docs

Variables d'environnement :
- `MLFLOW_TRACKING_URI` (défaut `sqlite:///mlflow.db`)
- `MODEL_NAME` (défaut `tetouan-pics-model`)
- `MODEL_ALIAS` (défaut `champion`)

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| GET | /health | 200 si le modèle est chargé, avec sa version |
| GET | /model | nom, version, run MLflow, seuil de décision, features |
| POST | /predict | une prédiction |
| POST | /predict/batch | plusieurs prédictions (`{"mesures": [...]}`, 1 à 5000) |

## Entrée de /predict

Ce que le système de dispatching connaît au moment t :

| Champ | Type | Contrainte |
|---|---|---|
| datetime | date ISO | obligatoire |
| temperature | float | entre -5 et 50 |
| humidity | float | entre 0 et 100 |
| wind_speed | float | entre 0 et 20 |
| general_diffuse_flows | float | entre 0 et 1500 |
| diffuse_flows | float | entre 0 et 1500 |
| total_kw | float | > 0 (consommation actuelle des 3 zones) |
| lag_10min, lag_1h, lag_24h | float | > 0 (consommation 10 min, 1 h, 24 h avant) |
| mean_1h | float | > 0 (moyenne de la dernière heure) |

Les features `hour_sin`, `hour_cos`, `dayofweek`, `is_weekend` et `diff_1h` sont calculées par
l'API avec la même fonction que le pipeline (`add_derived` dans `src/features.py`).

Une entrée qui ne respecte pas le contrat est refusée avec un code 422 et le détail du champ
en erreur. Exemple : `examples/mesure_invalide.json` (température -999 et `mean_1h` manquant).

## Sortie

```json
{
  "prediction_id": "90adc2d2-...",
  "datetime": "2017-07-15T20:00:00",
  "peak_probability": 0.992,
  "alert": true,
  "decision_threshold": 0.06,
  "model_version": "1"
}
```

`alert` = `peak_probability >= decision_threshold`. Chaque réponse contient la version du
modèle et un identifiant unique, pour pouvoir relier plus tard la prédiction à la vraie valeur
(feedback).
