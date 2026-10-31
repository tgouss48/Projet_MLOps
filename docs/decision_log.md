# Journal des décisions

On note ici les choix importants du projet, avec la raison et le fichier qui le prouve.

**D-001 : choix du cas métier**
Alerte de pic de consommation à H+1 pour le dispatching de Tétouan. On voulait des données
marocaines publiques, avec une vraie décision derrière.
Voir `docs/01_cadrage.md`.

**D-002 : jeu de données**
Jeu UCI n° 849 (licence CC BY 4.0, pas de valeurs manquantes). Le téléchargement et le
versionnement sont faits avec DVC (`dvc import-url`) plutôt qu'avec un script maison :
l'URL et le md5 du fichier sont dans `data/raw/tetouan.zip.dvc`.

**D-003 : découpage temporel**
Entraînement de janvier à avril, test en mai, production simulée de juin à décembre. L'été n'est
jamais vu à l'entraînement, ce qui va créer une dérive qu'on pourra surveiller.
Voir `params.yaml` (section protocol).

**D-004 : seuils**
Seuil de pic = P90 de la consommation sur l'entraînement. Seuil de décision choisi en minimisant
`5 x FN + FP`, parce qu'un pic raté coûte beaucoup plus cher qu'une fausse alerte.

**D-005 : critères d'acceptation fixés avant l'entraînement**
Rappel >= 0,85, précision >= 0,50, PR-AUC >= 0,80 et meilleur que la persistance.
Voir `docs/01_cadrage.md`.

**D-006 : validation des données avec pandera**
Plages de valeurs larges mais physiquement possibles (température entre -5 et 50 °C, humidité
entre 0 et 100 %, consommation > 0, etc.), pas de 10 minutes strict, colonnes imposées. Si une
règle échoue, le pipeline s'arrête et rien n'est produit en aval.
Voir `src/schema.py`, `tests/test_validate.py`, `reports/data_validation_rejet.json`.

**D-007 : features**
Uniquement des informations disponibles au moment de la prédiction : météo actuelle, heure
(encodée en sin/cos), jour de la semaine, consommation actuelle et passée (10 min, 1 h, 24 h).
Le mois n'est pas utilisé : le train ne contient que janvier à avril, le modèle ne saurait pas
quoi faire des autres mois.
Voir `src/features.py`, `tests/test_features.py`.

**D-008 : résultat du découpage**
Seuil de pic = 92 059 kW. Taux de pics : 10,1 % en train, 12,0 % en test, 17,2 % sur la
production simulée (jusqu'à environ 40 % en juillet et août).
Voir `reports/data_stats.json`.
