# Détection de dérive

## Principe

Une fois par semaine, on compare les données reçues en production avec les données
d'entraînement (janvier à avril 2017). Étape `drift` du pipeline (`src/drift.py`), résultats
dans `reports/drift.md` (tableau) et `reports/drift.json`.

En production réelle, cette analyse tournerait chaque lundi (tâche planifiée). Ici on la
rejoue sur toute la période de production (mai à décembre 2017) : c'est simulé.

## Indicateurs

| Indicateur | Calcul | Pourquoi |
|---|---|---|
| Consommation hors domaine | part des `total_kw` en dehors de [P1, P99] du train | le gradient boosting ne sait pas extrapoler : au delà de ce qu'il a vu, il répond comme pour la valeur maximale connue |
| PSI consommation | Population Stability Index de `total_kw` (10 tranches, quantiles du train) | mesure le changement de forme de la distribution |
| Température hors domaine | part des températures en dehors de [P1, P99] du train | conditions jamais vues |
| PSI météo | PSI de chaque variable météo | pour information seulement (voir plus bas) |

## Pourquoi pas les seuils PSI classiques sur toutes les variables

Avec les seuils habituels (PSI > 0,25 = dérive), presque toutes les semaines sont en dérive,
même en mai où le modèle est très bon (PSI température de 4,4 la première semaine de mai). La
météo change avec les saisons, c'est normal, et ça ne gêne pas forcément le modèle. Une alerte
qui sonne tout le temps finit par être ignorée. On a donc gardé comme déclencheurs les
indicateurs liés à la consommation, qui est l'information la plus importante pour le modèle.

## Règles de décision

Seuils dans `params.yaml` (section `drift`).

| Statut | Condition | Décision |
|---|---|---|
| STABLE | aucun seuil dépassé | rien |
| ATTENTION | consommation hors domaine > 10 %, ou PSI consommation > 0,5, ou température hors domaine > 30 % | surveiller de près la semaine suivante |
| DERIVE | consommation hors domaine > 20 %, ou (PSI consommation > 1 et hors domaine > 10 %) | prévenir l'équipe ; si 2 semaines de suite : réentraîner |

Exemple de décembre : la consommation est plus basse qu'à l'entraînement (PSI de 1,2) mais
elle reste dans les valeurs connues (1 % hors domaine). Statut ATTENTION et pas DERIVE : le
modèle n'est pas perdu, et en effet son coût reste faible.

## Résultats

- 14 semaines stables, 13 en attention, 8 en dérive
- les 8 semaines en dérive vont du 3 juillet au 27 août, exactement la période où le modèle
  rate 70 % des pics (rappel réel 0,27 à 0,31, coût de 224 à 296 par jour contre 8 en mai)
- retour à STABLE mi-septembre, quand la consommation redescend
- **décision : réentraîner à la fin de la semaine du 10 juillet**, avec les données
  disponibles jusqu'au 16 juillet

Le tableau complet contient aussi le rappel et le coût réels, calculés après coup avec la
vraie consommation. Ils servent à vérifier que les indicateurs de dérive suivent bien la
dégradation du modèle. En production on ne les a qu'avec une heure de retard (feedback).

## Lien avec le monitoring

L'alerte Prometheus `TemperatureHorsReference` (voir `docs/monitoring.md`) se déclenche en
direct quand la température moyenne dépasse 24 °C. Sa décision est de lancer cette analyse
de dérive sans attendre le lundi : `make drift`.

## Limites

- les seuils ont été choisis en regardant toute l'année 2017 ; on a vérifié qu'ils ne
  déclenchent pas sur mai (période de test, où le modèle est validé), mais idéalement il
  faudrait les valider sur une autre année
- les dates de début de semaine sont des lundis (la semaine du 1er mai est complète)
