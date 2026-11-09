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

- [ ] Le problème et l'utilisateur sont compréhensibles sans le catalogue.
- [ ] Le nombre de fonctionnalités correspond à la taille de l'équipe.
- [ ] Chaque fonctionnalité est démontrable (pas de formulation vague comme « améliorer »).
- [ ] Chaque composant technique a une justification d'une ligne.
- [ ] Le hors périmètre est rempli.

## Livrable 2 : dataset

Rédacteur : Gouraguine Zakaria   Relecteur : Aadoud Anass   Fichiers : `docs/semaine1/2-dataset.md` + `data/sample/`

Sans données utilisables dès la semaine 1, le projet ne peut pas tenir en 4 semaines. **Un échantillon réel doit déjà être dans le dépôt** (quelques fichiers ou une centaine de lignes, moins de 10 Mo). Les données complètes volumineuses ne vont pas dans Git : indiquez où elles se trouvent.

**2.1 Description**

| Rubrique | Réponse |
| --- | --- |
| Nom et source (lien) | \[à compléter\] |
| Producteur ou propriétaire | \[à compléter\] |
| Volume (nombre de fichiers, lignes, pages, taille) | \[à compléter\] |
| Format et structure (PDF, CSV, JSON, logs, images ; colonnes principales) | \[à compléter\] |
| Langue et période couverte | \[à compléter\] |
| Licence et droits d'usage | \[à compléter\] |
| Données personnelles ou sensibles, et traitement prévu | \[à compléter ou « aucune »\] |
| Emplacement des données complètes | \[à compléter\] |

**2.2 Qualité constatée sur l'échantillon** : valeurs manquantes, doublons, bruit, documents illisibles, déséquilibre. \[à compléter\]

**2.3 Justification** : pour chaque fonctionnalité du livrable 1, expliquez en une ligne en quoi ces données permettent de la réaliser.

| Fonctionnalité | Données utilisées | En quoi elles suffisent |
| --- | --- | --- |
| F1 |  |  |
| F2 |  |  |
| F3 |  |  |

**2.4 Alternative de repli** : si la source principale devient inaccessible ou se révèle inutilisable, quelle autre source (jeu public, données simulées ou générées) et ce que vous perdez en l'utilisant. \[à compléter\]

**2.5 Jeu de test** : comment vous mesurerez la qualité de l'agent. Taille (au moins 20 cas), origine, réponses attendues rédigées par qui. \[à compléter\]

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
