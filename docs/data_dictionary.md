# Dictionnaire de données

Source : Power Consumption of Tetouan City, UCI Machine Learning Repository (jeu n° 849)
https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city

- licence : CC BY 4.0
- période : du 01/01/2017 00:00 au 30/12/2017 23:50, une mesure toutes les 10 minutes
- taille : 52 416 lignes, 9 colonnes, aucune valeur manquante
- sha256 du CSV : `ca8b2f30cf07dd872cb7f2aa45dac110ee38dbe5fc5910a6ff4bcc530dae3a40`
- pas de données personnelles (consommation agrégée par zone)

## Colonnes

| Colonne d'origine | Nom utilisé | Unité | Description |
|---|---|---|---|
| DateTime | datetime | - | date et heure de la mesure (format M/D/YYYY H:MM) |
| Temperature | temperature | °C | température |
| Humidity | humidity | % | humidité relative |
| Wind Speed | wind_speed | m/s | vitesse du vent |
| general diffuse flows | general_diffuse_flows | W/m² | rayonnement solaire global diffus |
| diffuse flows | diffuse_flows | W/m² | rayonnement solaire diffus |
| Zone 1 Power Consumption | zone1_kw | kW | consommation zone Quads |
| Zone 2  Power Consumption | zone2_kw | kW | consommation zone Smir |
| Zone 3  Power Consumption | zone3_kw | kW | consommation zone Boussafou |

Remarque : les colonnes Zone 2 et Zone 3 ont un double espace dans leur nom d'origine.

Les plages de valeurs acceptées sont définies dans `src/schema.py` :

| Colonne | Règle |
|---|---|
| datetime | unique, une mesure toutes les 10 minutes |
| temperature | entre -5 et 50 |
| humidity | entre 0 et 100 |
| wind_speed | entre 0 et 20 |
| general_diffuse_flows, diffuse_flows | entre 0 et 1500 |
| zone1_kw, zone2_kw, zone3_kw | entre 0 (exclu) et 100 000 |

## Variables calculées

- `total_kw` = zone1_kw + zone2_kw + zone3_kw
- `hour_sin`, `hour_cos` : heure de la journée encodée de façon cyclique
- `dayofweek` (0 = lundi) et `is_weekend`
- `lag_10min`, `lag_1h`, `lag_24h` : total_kw 10 min, 1 h et 24 h avant
- `mean_1h` : moyenne de total_kw sur la dernière heure
- `diff_1h` : total_kw - lag_1h
- `peak_threshold_kw` = P90 de total_kw sur l'entraînement (92 059 kW)
- `target_peak_h1` = 1 si total_kw une heure plus tard dépasse peak_threshold_kw, sinon 0

Les premières 24 h (pas de lag_24h) et les lignes dont la cible tombe dans la période suivante
sont supprimées.
