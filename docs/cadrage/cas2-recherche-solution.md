# Fiche de cadrage : recherche de la solution citée (base de connaissances)

> Remplir chaque rubrique en une à trois phrases. Les rubriques marquées (obligatoire) sont vérifiées par `pytest`.

## Besoin en une phrase (obligatoire)

Les techniciens redonnent sans cesse les mêmes procédures simples : l'agent doit proposer à l'employé une procédure pas à pas, fiable et citée (par exemple `KB-NET-01`), adaptée à son incident.

## Utilisateur final (obligatoire)

L'employé, qui applique lui-même les étapes affichées dans le chat avant qu'un technicien n'intervienne.

## Approche retenue (obligatoire)

Cocher une seule case :

- [ ] Règles métier
- [ ] Machine learning
- [x] RAG
- [ ] Modèle génératif seul

Seule la partie « recherche » du RAG est utilisée : l'article retrouvé est affiché tel quel, sans génération de texte.

## Justification (obligatoire, citer au moins deux critères de la grille : (a) données étiquetées, (b) vérifiabilité, (c) coût par requête, (d) conséquence d'une erreur)

(b) Vérifiabilité : chaque réponse cite un article validé par le binôme, que l'employé et le technicien peuvent relire. (d) Conséquence d'une erreur : une procédure inventée pourrait faire perdre des données ou désactiver une protection, d'où l'absence de génération libre. (c) Coût : la recherche sémantique MiniLM tourne en local, en quelques millisecondes, sans API payante.

## Données nécessaires et leur origine (obligatoire)

La base de connaissances `data/sample/base_connaissances.csv` : 57 articles (titre, symptômes, étapes, condition d'escalade), environ 8 par catégorie, rédigés par le binôme d'après les pages publiques Microsoft Support (source citée dans la colonne `source`). Pour l'évaluation, chaque message des jeux de validation et indépendant indique les articles acceptés (colonne `articles_ok`).

## Métrique de succès et seuil d'acceptation (obligatoire)

Part des incidents dont un article accepté est proposé en 1re position (top-1) ≥ 75 %, et dans les 3 premiers (top-3) ≥ 90 %, sur le jeu indépendant. Vérification : `python -m support_agent.evaluer` (champs `top1` et `top3` du JSON).

## Conséquence d'une erreur et validation humaine prévue (obligatoire)

Un mauvais article fait perdre du temps à l'employé. Les garde-fous : la base est relue et validée par le binôme avant usage ; chaque article indique quand un technicien est nécessaire (`escalade_si`) ; au plus 2 articles sont proposés avant le ticket ; un article marqué « always » envoie tout de suite à un technicien.

## Risques éthiques ou de confidentialité (obligatoire)

Les procédures sont reformulées d'après des pages publiques, avec la source citée ; 31 articles sur 57 n'ont pas encore de source et doivent être complétés. Les étapes ne demandent jamais de mot de passe et ne font aucune action réelle sur le poste ou le compte (hors périmètre).

## Approche écartée et pourquoi (facultatif)

Modèle génératif seul (par exemple Ollama llama3.2) : réponses non vérifiables, risque d'inventer une commande ou un réglage dangereux. Il reste une option de reformulation, désactivée par défaut (`OLLAMA_ACTIVE=false`). Recherche TF-IDF seule : écartée après mesure (top-1 0,53 contre 0,84 avec MiniLM sur la validation).
