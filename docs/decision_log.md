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

**D-009 : choix du modèle sur une validation, pas sur le test**
Les 3 dernières semaines du train (10 au 30 avril) servent de validation. Le seuil de décision et
le meilleur modèle sont choisis dessus en minimisant `5 x FN + FP`, puis le modèle est
réentraîné sur tout le train. Le test de mai n'est utilisé qu'une fois, pour mesurer.
Voir `src/train.py`, `params.yaml` (section train).

**D-010 : modèle retenu = gradient boosting (HistGradientBoosting)**
Coût sur la validation : persistance 714, régression logistique 178, gradient boosting 113.
Sur le test le gradient boosting obtient rappel 0,867, précision 0,869, PR-AUC 0,947 et un coût
de 425 contre 1116 pour la persistance.
Remarque : sur le test la régression logistique a un coût un peu plus bas (390). On garde quand
même le choix fait sur la validation, sinon on utiliserait le test pour choisir et ce ne serait
plus une évaluation honnête.
Voir `reports/metrics.json` et les runs MLflow (expérience `tetouan-pics`).

**D-011 : seuil de décision bas (0,06)**
Comme un pic raté coûte 5 fois plus qu'une fausse alerte, le seuil optimal est très bas : on
déclenche une alerte dès que la probabilité de pic dépasse 6 %.

**D-012 : MLflow en local avec SQLite**
`mlflow.db` (non versionné) contient les runs. Chaque `dvc repro` qui relance l'entraînement crée
de nouveaux runs, ce qui garde l'historique des expériences. Le lien entre le modèle de `models/`
et son run se fait par `mlflow_run_id` dans `models/metadata.json`.

**D-013 : quality gate dans le pipeline**
La gate est une étape DVC après le train. Elle ne lit pas `reports/metrics.json` mais recharge
le modèle et refait les calculs sur le test, pour ne pas dépendre de ce que le script de train
a écrit. Contrôles : features attendues, probabilités valides, latence, rappel, précision,
PR-AUC, coût inférieur à la persistance, rappel sur les week-ends. Un seul contrôle KO suffit
pour refuser le modèle et arrêter le pipeline.
Voir `src/quality_gate.py`, `tests/test_quality_gate.py`.

**D-014 : deux contrôles ajoutés après l'étape 1**
En regardant les erreurs du modèle, on a vu que les week-ends sont moins bien prédits (rappel
0,83 contre 0,88 en semaine). On a ajouté un rappel minimum de 0,75 sur les week-ends, pour
refuser un modèle bon en moyenne mais mauvais sur ce sous-groupe. On a aussi ajouté une limite
de latence (50 ms) pour l'API. Ces deux seuils ont été fixés après avoir vu les résultats du
modèle, contrairement aux autres : on le signale.

**D-015 : cas nominal et cas de refus**
- nominal : gradient boosting, tous les contrôles OK, décision ACCEPTE
  (`reports/quality_gate.json`)
- refus : régression logistique entraînée sans l'historique de consommation. Bonne précision
  (0,92) et PR-AUC correcte (0,90), elle bat même la persistance, mais rappel de 0,60 et
  seulement 0,27 le week-end, donc décision REFUSE (`reports/quality_gate_models_refus.json`).
  Ça montre qu'un seul indicateur ne suffit pas pour accepter un modèle.
  Commande : `make demo-gate-refus`.

**D-016 : registre de modèles MLflow avec alias**
Un modèle accepté par la gate est enregistré dans `tetouan-pics-model`. Ses réglages (seuil de
décision, features, md5 des données, décision de la gate) sont stockés en tags de la version.
L'API ne charge pas un fichier mais `models:/tetouan-pics-model@champion` : pour changer de
modèle en production, ou revenir en arrière, il suffit de déplacer l'alias.
Le script refuse d'enregistrer un modèle dont la gate n'a pas dit ACCEPTE.
Voir `src/register.py`, `reports/registry.json`.

**D-017 : contrat d'API**
Le client envoie ce qu'il connaît au moment t (météo, consommation actuelle et passée). L'API
calcule les autres features avec la même fonction que le pipeline (`add_derived`), pour éviter
une différence entre l'entraînement et la production. Un test le vérifie
(`test_meme_resultat_que_le_pipeline`). Les plages acceptées sont les mêmes que dans la
validation des données : une valeur hors plage est refusée avec un code 422.
Voir `src/app.py`, `docs/api.md`, `tests/test_api.py`.

**D-018 : la réponse contient la version du modèle et un identifiant de prédiction**
Pour la traçabilité et pour le feedback plus tard (relier une prédiction à ce qui s'est
vraiment passé une heure après).

**D-019 : serveur MLflow dans docker compose**
Avec MLflow en local (SQLite), les modèles étaient enregistrés avec un chemin absolu de la
machine (`/home/...`), illisible depuis un conteneur. On lance donc un serveur MLflow dans
docker compose qui stocke la base et les modèles dans un volume et les sert en HTTP. Le
pipeline et l'API passent tous les deux par ce serveur : il n'y a qu'un seul registre.
Voir `docker-compose.yml`, `params.yaml` (mlflow.tracking_uri).

**D-020 : le modèle n'est pas copié dans l'image**
L'image contient le code, le registre contient le modèle. On peut changer de modèle ou faire
un rollback sans reconstruire l'image. Contrepartie : l'API a besoin du registre au démarrage.
Si elle ne peut pas charger le modèle, elle démarre mais répond 503 (testé dans
`test_sans_modele_repond_503`).
Voir `docs/deploiement.md`.

**D-021 : image de l'API légère et non root**
Dépendances séparées (`requirements-docker.txt`, avec mlflow-skinny), seulement 3 fichiers de
code copiés, utilisateur `appuser`, healthcheck sur `/health`. Les versions communes avec
`requirements.txt` doivent rester identiques dans les deux fichiers.
Voir `Dockerfile`, `.dockerignore`.
