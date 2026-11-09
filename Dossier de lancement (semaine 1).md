# Dossier de lancement (semaine 1)

Nov 9, 2026 · @Larhlimi

**Projet** : sujet 9, *Agent de support informatique* (Agent_support_info) · **Binôme** : Aadoud Anass (membre A), Gouraguine Zakaria (membre B)

## Mode d'emploi

La semaine 1 est décisive : sur un projet de 4 semaines, un cadrage flou ou des données indisponibles ne se rattrapent pas. Ce dossier permet à l'enseignant de valider, faire reprendre ou refuser le projet sous 48 heures.

Le dossier comporte quatre livrables. **L'équipe se les répartit : chaque membre rédige seul le ou les livrables dont il est responsable, puis un autre membre le relit.** Le nom du rédacteur et du relecteur figure en tête de chaque livrable ; c'est une preuve de contribution pour la note individuelle.

**Répartition selon la taille de l'équipe**

| Taille | Membre A | Membre B | Membre C | Membre D |
| --- | --- | --- | --- | --- |
| 2 étudiants | 1. Descriptif + 3. Maquette | 2. Dataset + 4. Pipeline |  |  |
| 3 étudiants | 1. Descriptif + 4. Pipeline (consolidation) | 2. Dataset | 3. Maquette |  |
| 4 étudiants | 1. Descriptif | 2. Dataset | 3. Maquette | 4. Pipeline (consolidation) |

Le pipeline des tâches (livrable 4) est consolidé par un seul membre, mais **chaque membre y ajoute lui-même ses propres tâches**.

**Notre répartition**

| Livrable | Rédacteur | Relecteur | Fichier dans le dépôt |
| --- | --- | --- | --- |
| 1. Descriptif du projet | Aadoud Anass | Gouraguine Zakaria | `docs/semaine1/1-descriptif.md` |
| 2. Dataset | Gouraguine Zakaria | Aadoud Anass | `docs/semaine1/2-dataset.md` + `data/sample/` |
| 3. Maquette globale | Aadoud Anass | Gouraguine Zakaria | `docs/semaine1/3-maquette.md` + `docs/semaine1/img/` |
| 4. Pipeline des tâches | Gouraguine Zakaria | Aadoud Anass | `docs/semaine1/4-pipeline.md` |

**Circuit GitHub**

1. Le coordinateur (Aadoud Anass) crée le dossier `docs/semaine1/` avec un `README.md` qui reprend le tableau « Notre répartition ».
2. Chaque rédacteur copie la section de son livrable dans le fichier indiqué, travaille sur sa propre branche (`semaine1/descriptif`, `semaine1/dataset`, `semaine1/maquette`, `semaine1/pipeline`) et ouvre une pull request.
3. Le relecteur vérifie les critères d'acceptation du livrable, commente dans la pull request, puis l'approuve.
4. Une pull request n'est fusionnée qu'après approbation. Les quatre livrables sont fusionnés sur la branche principale avant la date limite.
5. Le coordinateur pose l'étiquette `semaine1-remis` sur le dernier commit et en informe l'enseignant.

## Livrable 1 : descriptif du projet mis à jour

Rédacteur : Aadoud Anass   Relecteur : Gouraguine Zakaria   Fichier : `docs/semaine1/1-descriptif.md`

**1.1 Contexte et problème.** Dans une entreprise, les employés signalent leurs incidents informatiques (VPN qui décroche, compte bloqué, imprimante, courriel suspect…) par courriel ou par téléphone au support. Les techniciens de niveau 1 passent l'essentiel de leur temps à trier ces messages et à redonner les mêmes procédures simples, ce qui retarde les vrais cas critiques (sécurité, panne générale). Aujourd'hui, tout passe par un humain : pas de tri automatique, pas de solution proposée avant l'ouverture d'un ticket, tickets souvent incomplets.

**1.2 Objectif** : un agent de support de premier niveau qui, à partir d'un incident décrit en anglais, le classe, propose en moins de 2 secondes une procédure pas à pas tirée d'une base de connaissances validée, et n'ouvre un ticket pré-rempli vers le bon groupe de techniciens que si l'incident n'est pas résolu ou est critique.

**1.3 Utilisateurs cibles et scénario d'usage principal.** Utilisateur principal : l'employé qui rencontre un incident. Utilisateur secondaire : le technicien qui reçoit les tickets escaladés.

1. L'employé ouvre la page de l'agent et décrit son problème (« My VPN keeps disconnecting every 10 minutes »).
2. L'agent classe l'incident (catégorie et priorité) et affiche l'article de la base le plus pertinent, avec ses étapes et sa référence (KB-NET-01), plus deux autres articles possibles.
3. L'employé suit les étapes et répond « résolu » ou « pas résolu ».
4. Si ce n'est pas résolu, l'agent propose un autre article ou pose une question de précision.
5. Après deux tentatives sans succès, sur demande, ou tout de suite pour un cas critique (sécurité, panne générale), l'agent propose un ticket pré-rempli (catégorie, priorité, groupe, articles déjà essayés) et ne le crée qu'après confirmation.
6. L'employé suit ensuite son ticket par son identifiant ; le technicien le reçoit déjà trié.

**1.4 Fonctionnalités du MVP** (binôme : 3)

| N° | Fonctionnalité | Ce que l'utilisateur voit ou obtient | Priorité (indispensable, souhaitable) |
| --- | --- | --- | --- |
| F1 | Classement de l'incident et proposition de solution dans une conversation | La catégorie, la priorité et une procédure pas à pas citée (identifiant et titre de l'article), puis la question « Is it solved? » ; les messages hors sujet sont refusés poliment | Indispensable |
| F2 | Escalade et ticket pré-rempli | Après deux échecs, sur demande ou pour un cas critique : un ticket avec catégorie, priorité, groupe d'escalade, motif et articles essayés, créé après confirmation, puis suivi par son identifiant | Indispensable |
| F3 | Traitement d'un fichier de tickets et statistiques | Un CSV d'incidents déposé, trié par l'agent (catégorie, priorité, article proposé, cas critiques signalés), et une page de statistiques (tickets par catégorie, taux de résolution, avis utile / pas utile) | Souhaitable |

**1.5 Services et composants techniques**

| Service ou composant | Rôle dans le projet | Technologie choisie | Pourquoi ce choix |
| --- | --- | --- | --- |
| Modèle (LLM ou ML) | Classer l'incident (7 catégories IT + hors sujet), estimer la priorité, s'abstenir quand il doute | scikit-learn : TF-IDF mots + caractères et vecteurs all-MiniLM-L6-v2 (sentence-transformers), LinearSVC calibré ; seuil d'abstention 0,60 | Données étiquetées disponibles, réponse en ~0,1 s sans GPU ni coût par appel, résultat mesurable et reproductible |
| Recherche ou mémoire (RAG, base vectorielle, SGBD) | Trouver les articles de la base de connaissances les plus proches de l'incident ; garder tickets, conversations et avis | Recherche hybride TF-IDF + MiniLM sur `base_connaissances.csv` (57 articles) ; stockage en fichiers JSON Lines | La solution doit venir d'un article validé et cité ; 57 articles ne justifient pas une base vectorielle ; JSON Lines suffit pour un agent de niveau 1 et garde l'historique |
| Outils appelés par l'agent | Règles d'escalade (groupe, cas critiques), création et suivi de ticket, reformulation optionnelle | Fonctions Python (`api/tickets.py`, `api/conversation.py`) ; Ollama (llama3.2) en option, désactivé par défaut | Une escalade doit être explicable et testée règle par règle ; le LLM local ne fait que reformuler un article existant, sans coût ni envoi de données à un tiers |
| API | Exposer l'agent : `/chat`, `/assist`, `/predict`, `/tickets`, `/feedback`, `/stats`, `/health` | FastAPI | Schémas Pydantic validés à l'entrée, documentation `/docs` automatique, tests faciles avec `TestClient` |
| Interface | Conversation, suivi d'un ticket, statistiques, fichier de tickets | Streamlit (4 onglets) | Interface en Python en quelques dizaines de lignes, suffisante pour la démonstration |
| Conteneur et intégration continue | Lancer API + interface en une commande ; vérifier chaque push | Docker, GitHub Actions | La CI existe déjà (ruff, mypy, pytest, couverture ≥ 95 %) ; Docker reste à écrire pour un déploiement reproductible |

**1.6 Hors périmètre** : messages dans une autre langue que l'anglais (orientés vers un humain, pas traduits) ; actions réelles sur le poste ou le compte de l'utilisateur (réinitialiser un mot de passe, redémarrer un service) ; authentification des utilisateurs et gestion des droits ; intégration à un vrai outil ITSM (GLPI, ServiceNow) ; réponse générée librement par un LLM sans article source ; pièces jointes et captures d'écran.

**1.7 Écart avec la fiche du catalogue.** Ajouts : la priorité de l'incident, l'abstention (`INDETERMINE` vers le tri N1) quand le modèle doute, le refus des messages hors sujet, et l'onglet fichier de tickets (F3). Modification : « répondre aux problèmes » se fait uniquement à partir d'articles validés et cités (recherche de type RAG, sans génération libre), pour qu'une procédure inventée ne puisse pas faire perdre des données. Retrait : aucun.

**Critères d'acceptation (vérifiés par le relecteur)**

- [x] Le problème et l'utilisateur sont compréhensibles sans le catalogue.
- [x] Le nombre de fonctionnalités correspond à la taille de l'équipe.
- [x] Chaque fonctionnalité est démontrable (pas de formulation vague comme « améliorer »).
- [x] Chaque composant technique a une justification d'une ligne.
- [x] Le hors périmètre est rempli.

## Livrable 2 : dataset

Rédacteur : Gouraguine Zakaria   Relecteur : Aadoud Anass   Fichiers : `docs/semaine1/2-dataset.md` + `data/sample/`

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

**Échantillon dans `data/sample/`** : `tobi_bueck_extrait.csv` (100 incidents en anglais nettoyés comme dans `src/train.py`, 14 ou 15 par catégorie, colonnes `text`, `categorie`, `priorite`), `base_connaissances.csv` (57 articles), `jeu_or.csv` (20 incidents avec catégorie attendue). 78 Ko au total.

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

**Critères d'acceptation (vérifiés par le relecteur)**

- [ ] L'échantillon est dans `data/sample/` et s'ouvre sans erreur.
- [ ] La licence autorise l'usage dans un projet de cours.
- [ ] Les données personnelles éventuelles sont anonymisées ou remplacées par des données fictives.
- [ ] Chaque fonctionnalité du MVP est couverte par la justification.
- [ ] L'alternative de repli est réellement accessible (lien vérifié).
- [ ] Le jeu de test est défini, même partiellement rédigé.

## Livrable 3 : maquette globale

Rédacteur : Aadoud Anass   Relecteur : Gouraguine Zakaria   Fichiers : `docs/semaine1/3-maquette.md` + `docs/semaine1/img/`

La maquette comporte deux vues : l'architecture (comment le système fonctionne) et les écrans (ce que voit l'utilisateur).

**3.1 Schéma d'architecture.** Montrez les composants du livrable 1, les flux de données et le parcours d'une requête de l'utilisateur jusqu'à la réponse. Écrivez-le en Mermaid dans le fichier Markdown (GitHub l'affiche directement) ou déposez une image dans `img/`. \[à compléter\]

**3.2 Légende du schéma** : une ligne par composant, avec la fonctionnalité (F1, F2...) qu'il sert. \[à compléter\]

**3.3 Maquette des écrans.** 2 à 4 écrans principaux, dessinés à la main et photographiés, ou faits avec l'outil de votre choix. Pour chaque écran :

| Écran | Image (`img/...`) | Fonctionnalités affichées | Action principale de l'utilisateur |
| --- | --- | --- | --- |
| \[à compléter\] |  |  |  |
| \[à compléter\] |  |  |  |
|  |  |  |  |

**3.4 Parcours utilisateur** : enchaînement des écrans pour le scénario principal du livrable 1 (écran A, action, écran B...). \[à compléter\]

**Critères d'acceptation (vérifiés par le relecteur)**

- [ ] Chaque composant du livrable 1 apparaît dans le schéma, et inversement.
- [ ] Le parcours d'une requête se suit de bout en bout sur le schéma.
- [ ] Chaque fonctionnalité du MVP est visible sur au moins un écran.
- [ ] Le schéma s'affiche correctement sur GitHub (Mermaid valide ou image présente).
- [ ] Pour une équipe de 4 : les agents ou sous-systèmes et leurs échanges sont représentés.

## Livrable 4 : pipeline des tâches prévues

Consolidateur : Gouraguine Zakaria   Relecteur : Aadoud Anass   Fichier : `docs/semaine1/4-pipeline.md`

Le pipeline découpe le projet en tâches de 1 à 2 jours. **Chaque membre saisit lui-même ses tâches** ; le consolidateur vérifie les dépendances et l'équilibre de la charge. Les tâches sont aussi créées comme issues GitHub (ou dans un tableau GitHub Projects) pour être suivies dans le rapport hebdomadaire.

**4.1 Liste des tâches**

| ID | Tâche | Fonctionnalité | Responsable | Dépend de | Semaine | Terminée quand ? (critère vérifiable) |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | \[à compléter\] |  |  |  | 1 |  |
| T2 |  |  |  |  |  |  |
| T3 |  |  |  |  |  |  |
| T4 |  |  |  |  |  |  |

**4.2 Jalons hebdomadaires** (repris de la fiche de cadrage)

| Semaine | Jalon démontrable | Tâches qui y mènent |
| --- | --- | --- |
| 1 | Dossier de lancement fusionné, prototype en script |  |
| 2 | Agent exposé par l'API, premiers tests |  |
| 3 | MVP complet, Docker et CI au vert |  |
| 4 | Résultats mesurés, code gelé, soutenance |  |

**4.3 Vue chronologique.** Diagramme de Gantt en Mermaid. \[à compléter\]

**4.4 Chemin critique et charge**

- Chaîne de tâches dont le moindre retard décale la soutenance : \[à compléter\]
- Charge par membre (nombre de jours de tâches) : \[à compléter\]

**Critères d'acceptation (vérifiés par le relecteur)**

- [ ] Aucune tâche ne dépasse 2 jours.
- [ ] Chaque fonctionnalité du MVP a au moins une tâche, et chaque tâche a un critère de fin vérifiable.
- [ ] Le MVP est complet au plus tard en fin de semaine 3.
- [ ] Chaque membre a saisi ses propres tâches ; l'écart de charge entre membres reste inférieur à 2 jours.
- [ ] Les tâches existent comme issues GitHub.

## Remise et décision de l'enseignant

**Checklist de remise (coordinateur : Aadoud Anass)**

- [ ] `docs/semaine1/README.md` avec la répartition rédacteurs et relecteurs
- [ ] Les quatre livrables fusionnés sur la branche principale, chacun par une pull request approuvée par son relecteur
- [ ] Échantillon de données dans `data/sample/`
- [ ] Schéma et écrans visibles sur GitHub
- [ ] Issues GitHub créées pour les tâches du pipeline
- [ ] Étiquette `semaine1-remis` posée et enseignant prévenu

**Décision de l'enseignant (sous 48 heures)**

Un seul critère bloquant suffit pour que le dossier soit à reprendre ; un dossier à reprendre est corrigé et remis sous 48 heures.

| Critère | Type | Respecté | Commentaire |
| --- | --- | --- | --- |
| Données accessibles et échantillon présent (L2) | Bloquant | ☐ |  |
| MVP réaliste en 4 semaines pour cette taille d'équipe (L1, L4) | Bloquant | ☐ |  |
| Livrables répartis, chacun avec un rédacteur et un relecteur distincts | Bloquant | ☐ |  |
| Licence et données personnelles traitées (L2) | Bloquant | ☐ |  |
| Architecture cohérente avec les fonctionnalités (L1, L3) | À améliorer | ☐ |  |
| Écrans couvrant tout le MVP (L3) | À améliorer | ☐ |  |
| Tâches courtes, critères de fin vérifiables, charge équilibrée (L4) | À améliorer | ☐ |  |
| Alternative de repli et jeu de test définis (L2) | À améliorer | ☐ |  |

**Décision** : ☐ Validé   ☐ À reprendre   ☐ Refusé (changement de sujet)

Date et visa : \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Lien avec l'évaluation.** Ce dossier sert de référence pour le critère P1 (respect du cadrage) et alimente P3 (jeu de test et indicateurs) et P7 (pipeline et suivi). La répartition et les pull requests de chaque membre comptent comme preuves pour le coefficient individuel.
