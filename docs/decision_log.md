# Journal des décisions

On note ici les choix importants du projet, avec la raison et le fichier qui le prouve.

**D-001 : choix du cas métier**
Alerte de pic de consommation à H+1 pour le dispatching de Tétouan. On voulait des données
marocaines publiques, avec une vraie décision derrière.
Voir `docs/01_cadrage.md`.

**D-002 : jeu de données**
Jeu UCI n° 849 (licence CC BY 4.0, pas de valeurs manquantes). La source et le sha256 du
fichier sont notés dans `params.yaml`. Le téléchargement et le versionnement seront faits avec
DVC plutôt qu'avec un script maison.

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
