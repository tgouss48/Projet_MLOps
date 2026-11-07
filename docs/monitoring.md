# Observabilité

`make up` lance, en plus de MLflow et de l'API :
- Prometheus (http://localhost:9090) : collecte `/metrics` de l'API toutes les 5 s et évalue
  les règles d'alerte (`monitoring/alerts.yml`). Onglet *Alerts* pour voir leur état.
- Grafana (http://localhost:3000) : tableau de bord « Tetouan - API de prediction des pics »
  chargé automatiquement (accès en lecture sans mot de passe, admin/admin pour modifier).

## Métriques exposées par l'API

| Métrique | Type | Ce qu'elle mesure |
|---|---|---|
| `api_requests_total{route,status}` | compteur | requêtes par route et code retour |
| `api_request_duration_seconds{route}` | histogramme | latence |
| `api_invalid_inputs_total{champ}` | compteur | champs refusés par le contrat (422) |
| `model_loaded` | jauge | 1 si un modèle est chargé |
| `model_info{version,algo}` | jauge | version servie |
| `predictions_total{alert}` | compteur | prédictions, avec ou sans alerte |
| `peak_probability` | histogramme | probabilités prédites |
| `input_temperature_celsius` | histogramme | températures reçues |
| `input_total_kw` | histogramme | consommations reçues |

Code : `src/metrics.py` et le middleware dans `src/app.py`.

## Alertes, seuils et décisions

| Alerte | Condition | Pendant | Décision |
|---|---|---|---|
| ApiIndisponible | Prometheus ne joint plus l'API | 30 s | redémarrer le conteneur, lire les logs ; le dispatching repasse en surveillance manuelle |
| ModeleNonCharge | `model_loaded == 0` | 30 s | vérifier le serveur MLflow et l'alias `champion`, redémarrer l'API |
| LatenceElevee | p95 de /predict > 200 ms | 1 min | regarder la charge de la machine et la taille des lots |
| Erreurs5xx | > 1 % de 5xx | 1 min | lire les logs ; si ça vient d'une nouvelle version du modèle : rollback |
| EntreesInvalides | > 5 % de 422 sur /predict | 30 s | voir quel champ est refusé : capteur en panne ou changement côté client |
| TauxAlertesAnormal | > 30 % d'alertes sur 5 min (10 % au train, 12 % en mai) | 1 min | période vraiment chargée ou dérive : lancer l'analyse de dérive |
| TemperatureHorsReference | température moyenne > 24 °C sur 5 min (P99 du train : 24,4 °C) | 1 min | le modèle n'a jamais vu ces conditions : analyse de dérive, préparer un réentraînement |

Les seuils de latence et d'erreurs viennent des objectifs de service du cadrage. Les durées
(`for`) sont courtes pour pouvoir montrer les alertes en démonstration ; en vrai on mettrait
plutôt 5 à 15 minutes.

Limite : les alertes sont visibles dans Prometheus et Grafana mais ne sont envoyées nulle
part (pas d'Alertmanager, pas de mail).

## Scénarios

`scripts/simulate_traffic.py` envoie de vraies mesures à l'API, une par une, puis enregistre
les métriques et les alertes Prometheus dans `reports/monitoring_<scenario>.json`.

| Scénario | Commande | Requêtes | Résultat |
|---|---|---|---|
| stable : mesures de mai | `make simu-stable` | 1237, toutes en 200 | p95 34 ms, 9,5 % d'alertes du modèle, 20,4 °C en moyenne, **aucune alerte** |
| capteur en panne : mai, 30 % de températures à -999 | `make simu-capteur` | 30 % en 422 | **EntreesInvalides** ; le modèle n'est pas touché (les mesures invalides n'arrivent pas jusqu'à lui) |
| été : mesures de juillet | `make simu-ete` | 3745, toutes en 200 | 27,4 °C en moyenne, **TemperatureHorsReference** ; taux d'alertes du modèle 15,5 %, donc pas d'alerte TauxAlertesAnormal |
| panne de l'API | `docker compose stop api` | - | **ApiIndisponible** au bout de 30 s |

## Ce que montre le scénario été

On a recalculé hors ligne les performances du modèle mois par mois sur la période de
production (on connaît la vraie réponse) :

| Mois | Vrais pics | Alertes du modèle | Rappel | Précision |
|---|---|---|---|---|
| mai (test) | 12 % | 12 % | 0,87 | 0,87 |
| juin | 21 % | 14 % | 0,59 | 0,85 |
| juillet | 43 % | 15 % | 0,33 | 0,99 |
| août | 39 % | 13 % | 0,33 | 0,97 |
| septembre | 8 % | 11 % | 0,97 | 0,70 |
| novembre | 2 % | 12 % | 0,85 | 0,11 |

En été le modèle rate 2 pics sur 3, mais son taux d'alertes reste autour de 15 % : vu de
l'extérieur il a l'air normal. Les métriques de service (latence, erreurs) sont parfaites. La
dégradation est donc silencieuse. Elle n'est visible que :
1. par la dérive des entrées (alerte TemperatureHorsReference) ;
2. en comparant les prédictions avec la vraie consommation une heure plus tard (feedback).

C'est ce qui justifie les étapes suivantes : analyse de dérive, puis feedback et réentraînement.
