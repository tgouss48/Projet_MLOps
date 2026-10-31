# Cadrage du projet

## Contexte

La ville de Tétouan est alimentée par trois zones de distribution : Quads, Smir et Boussafou.
En été la consommation augmente beaucoup (climatisation, touristes sur la côte à M'diq, Martil
et Cabo Negro, retour des MRE). Quand un pic n'est pas prévu, le distributeur doit acheter de
l'énergie en urgence, ce qui coûte cher, ou faire du délestage.

## Problème et décision

L'utilisateur visé est l'opérateur du centre de dispatching. Toutes les 10 minutes, il doit
décider s'il active une réserve ou prépare un plan d'effacement pour l'heure suivante.

On transforme ça en problème de classification binaire : est-ce que la consommation totale de
la ville va dépasser le seuil de pic dans 60 minutes ?

- cible : `target_peak_h1` = 1 si `total_kw(t + 60 min)` > seuil de pic, 0 sinon
- seuil de pic : 90e percentile de la consommation totale sur la période d'entraînement (environ 92 059 kW). Il est calculé une fois et ne bouge plus.
- sortie du modèle : une probabilité et la décision (alerte ou pas)

## Coût des erreurs

Les deux erreurs n'ont pas le même coût :
- rater un pic (faux négatif) peut mener à un délestage, donc des clients coupés ;
- une fausse alerte (faux positif) fait juste activer la réserve pour rien.

On a considéré qu'un pic raté coûte 5 fois plus qu'une fausse alerte. Le seuil de décision ne
sera donc pas 0,5 : on le choisira pour minimiser `5 x FN + FP`. Le rappel sur les pics est
la métrique la plus importante pour nous.

## Critères d'acceptation

On les a fixés avant d'entraîner quoi que ce soit, pour ne pas adapter les seuils au résultat.

Modèle (sur le jeu de test) :
- rappel sur la classe pic >= 0,85
- précision sur la classe pic >= 0,50
- PR-AUC >= 0,80
- coût métier plus faible que la baseline de persistance

La baseline de persistance est la règle « s'il y a un pic maintenant, il y en aura un dans une
heure ». Si le modèle ne fait pas mieux que ça, il ne sert à rien et il est refusé.

Service :
- latence p95 < 200 ms
- moins de 1 % d'erreurs 5xx

## Protocole d'évaluation

Le découpage est temporel (pas de découpage aléatoire, sinon on aurait de la fuite entre des
mesures espacées de 10 minutes). Les dates sont dans `params.yaml`.

- entraînement : du 01/01 au 30/04/2017
- test : du 01/05 au 31/05/2017
- production simulée : du 01/06 au 30/12/2017, rejouée semaine par semaine dans l'API

Pour éviter les fuites :
- le seuil de pic et les statistiques de référence sont calculés seulement sur l'entraînement
- les features utilisent uniquement le passé (lags, moyennes glissantes)
- on supprime les dernières lignes de chaque période quand leur cible tombe dans la période suivante

## Choix du modèle

On compare une baseline de persistance, une régression logistique et un gradient boosting.
L'entraînement prend moins d'une minute en local. Pas de deep learning, ça n'apporterait rien
sur des données tabulaires de cette taille.

## Risques

- Dérive saisonnière : elle est quasi certaine. Le seuil de pic est dépassé environ 10 % du temps en
  hiver contre 43 % en juillet. C'est justement ce qu'on veut détecter avec le monitoring, puis
  traiter par un réentraînement.
- Capteur météo en panne ou valeurs aberrantes : les entrées de l'API seront validées et les
  requêtes invalides rejetées.
- Une seule année de données (2017) : on ne peut pas tester sur une autre année, c'est une
  limite du projet.
- Ramadan 2017 (fin mai à fin juin) : les habitudes horaires changent, ça peut aussi créer de la dérive.
- Le seuil de pic peut devenir obsolète : il sera revu à chaque réentraînement.

## Hors périmètre

Kubernetes, cloud payant, prévision sur plusieurs horizons, optimisation réelle du dispatching.
Ce qui est simulé (notamment le flux de production) sera indiqué dans le rapport.
