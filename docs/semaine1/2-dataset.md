# Livrable 2 : dataset

Rédacteur : Gouraguine Zakaria   Relecteur : Aadoud Anass   Fichiers : `docs/semaine1/2-dataset.md` + `data/sample/`

Retour à la répartition : [README](README.md)

**2.1 Description**

| Rubrique | Réponse |
| --- | --- |
| Nom et source (lien) | (1) `Tobi-Bueck/customer-support-tickets`, https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets ; (2) base de connaissances `data/base_connaissances.csv` ; (3) jeux d'évaluation de l'équipe (`jeu_or.csv`, `jeu_validation.csv`, `jeu_independant.csv`, `conversations_30.csv`) |
| Producteur ou propriétaire | (1) Tobias Bueck, publié sur Hugging Face (tickets fictifs générés) ; (2) et (3) le binôme, à partir des pages d'aide publiques Microsoft Support (source citée dans chaque article) |
| Volume (nombre de fichiers, lignes, pages, taille) | (1) 1 fichier parquet de 24 Mo (partie train) : 61 765 tickets, dont 28 261 en anglais et 11 213 incidents en anglais ; 8 452 incidents gardés après nettoyage (catégorie IT et priorité connues), 60 mots en moyenne ; (2) 57 articles, 32 Ko ; (3) 20 + 120 + 126 incidents et 30 conversations ; jeu de démonstration synthétique de 1 840 lignes généré par `src/make_demo.py` |
| Format et structure (PDF, CSV, JSON, logs, images ; colonnes principales) | (1) Parquet : `subject`, `body`, `answer`, `type`, `priority`, `language`, `queue`, `tag_1` à `tag_8` ; (2) CSV : `id`, `categorie`, `titre`, `symptomes`, `etapes` (séparées par `\|`), `escalade_si`, `source` ; (3) CSV : `text`, `attendu`, `difficulte`, `articles_ok` |
| Langue et période couverte | Anglais ; tickets non datés (jeu généré), base rédigée en novembre 2026 |
| Licence et droits d'usage | (1) CC BY-NC 4.0 : usage non commercial autorisé, donc compatible avec un projet de cours ; (2) et (3) rédigés par le binôme, procédures reformulées d'après Microsoft Support avec la source citée |
| Données personnelles ou sensibles, et traitement prévu | Aucune réelle : tickets fictifs et incidents écrits par le binôme. Les incidents saisis pendant la démonstration restent hors de Git (`tickets/` ignoré) et ne sont envoyés à aucun service tiers |
| Emplacement des données complètes | Tobi-Bueck : téléchargé depuis Hugging Face par `python src/historique.py --reel` et `python src/train.py --reel`, rangé dans `data/tobi_bueck.parquet` (ignoré par Git) ; base et jeux d'évaluation : versionnés dans `data/` |

**Échantillon dans [`data/sample/`](../../data/sample/)** ([`tobi_bueck_extrait.csv`](../../data/sample/tobi_bueck_extrait.csv), [`base_connaissances.csv`](../../data/sample/base_connaissances.csv), [`jeu_or.csv`](../../data/sample/jeu_or.csv)) : `tobi_bueck_extrait.csv` (100 incidents en anglais nettoyés comme dans `src/train.py`, 14 ou 15 par catégorie, colonnes `text`, `categorie`, `priorite`), `base_connaissances.csv` (57 articles), `jeu_or.csv` (20 incidents avec catégorie attendue). 78 Ko au total.

**2.2 Qualité constatée sur l'échantillon.**
- Tobi-Bueck : textes longs (courriels de plusieurs paragraphes), loin des messages courts tapés dans une conversation ; doublons retirés au nettoyage ; pas de catégorie IT fournie, elle est déduite des tags (sur 11 213 incidents en anglais, 8 452 restent après retrait des doublons, des textes trop courts et des incidents sans tag reconnu) ; les priorités ne suivent pas une règle cohérente (un modèle appris dessus n'atteint que 50 % de priorité exacte).
- Déséquilibre : `logiciel` (2 868) et `securite` (2 229) dominent, `compte_acces` (374) et `facturation` (269) sont rares ; le jeu de démonstration est équilibré par construction.
- Fuite repérée : 94 % des phrases de test du jeu de démonstration partageaient leur symptôme avec l'entraînement ; d'où les jeux de validation et indépendant, écrits à part et contrôlés par `tests/test_evaluer.py`.
- Base de connaissances : complète (aucune valeur manquante), au moins 6 articles par catégorie.

**2.3 Justification**

| Fonctionnalité | Données utilisées | En quoi elles suffisent |
| --- | --- | --- |
| F1 | Jeu de démonstration + Tobi-Bueck (entraînement du classement) ; base de 57 articles (solutions) | Exemples étiquetés pour les 7 catégories et le hors sujet ; chaque catégorie a au moins 6 procédures validées et citées |
| F2 | Sorties du modèle (catégorie, confiance, priorité) + colonne `escalade_si` de la base + table des groupes d'escalade | Les règles d'escalade n'ont besoin que de ces champs ; les 30 conversations vérifient qu'un ticket part au bon moment (10 tickets attendus) |
| F3 | `jeu_independant.csv` (126 messages, dont 32 cas critiques) comme fichier de démonstration ; tickets JSON Lines pour les statistiques | Un vrai lot à trier avec la réponse attendue, qui permet de compter tickets à tort et cas critiques manqués |

**2.4 Alternative de repli.** Si Tobi-Bueck devient inaccessible : le jeu synthétique de `src/make_demo.py` (1 840 incidents, généré sans réseau, déjà utilisé par la CI) suffit à entraîner le modèle livré ; il est déjà dans le dépôt, donc toujours accessible. Ce que l'on perd : la mesure sur des tickets « réels » longs et le mode `--mixte` ; le classement reste mesuré sur nos jeux de validation et indépendant.

**2.5 Jeu de test.**
- `jeu_or.csv` : 20 incidents (dont 10 difficiles), catégorie attendue, rédigés par le binôme (TP4).
- `jeu_validation.csv` : 120 messages pour régler le modèle, avec les articles qui règlent chaque incident (`articles_ok`).
- `jeu_independant.csv` : 126 messages (112 incidents, 14 hors sujet, 32 cas critiques), lu **une seule fois** pour la mesure finale.
- `conversations_30.csv` : 30 conversations complètes avec le scénario attendu (résolu, ticket, cas critique).
- Réponses attendues écrites par le binôme d'après le texte des articles, sans faire tourner l'agent. Indicateurs : F1 macro (seuil 0,85), top-1 et top-3 des articles (seuils 75 % et 90 %), cas critiques manqués (au plus 1), hors sujet refusé (au moins 90 %).

## Critères d'acceptation (vérifiés par le relecteur)

- [ ] L'échantillon est dans `data/sample/` et s'ouvre sans erreur.
- [ ] La licence autorise l'usage dans un projet de cours.
- [ ] Les données personnelles éventuelles sont anonymisées ou remplacées par des données fictives.
- [ ] Chaque fonctionnalité du MVP est couverte par la justification.
- [ ] L'alternative de repli est réellement accessible (lien vérifié).
- [ ] Le jeu de test est défini, même partiellement rédigé.
