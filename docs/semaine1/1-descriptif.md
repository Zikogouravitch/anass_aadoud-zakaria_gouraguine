# Livrable 1 : descriptif du projet mis à jour

Rédacteur : Aadoud Anass   Relecteur : Gouraguine Zakaria   Fichier : `docs/semaine1/1-descriptif.md`

Retour à la répartition : [README](README.md)

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
| Recherche ou mémoire (RAG, base vectorielle, SGBD) | Trouver les articles de la base de connaissances les plus proches de l'incident ; garder tickets, conversations et avis | Recherche hybride TF-IDF + MiniLM sur [`data/base_connaissances.csv`](../../data/base_connaissances.csv) (57 articles) ; stockage en fichiers JSON Lines ([`api/stockage.py`](../../api/stockage.py)) | La solution doit venir d'un article validé et cité ; 57 articles ne justifient pas une base vectorielle ; JSON Lines suffit pour un agent de niveau 1 et garde l'historique |
| Outils appelés par l'agent | Règles d'escalade (groupe, cas critiques), création et suivi de ticket, reformulation optionnelle | Fonctions Python ([`api/tickets.py`](../../api/tickets.py), [`api/conversation.py`](../../api/conversation.py)) ; Ollama (llama3.2) en option ([`api/llm.py`](../../api/llm.py)), désactivé par défaut | Une escalade doit être explicable et testée règle par règle ; le LLM local ne fait que reformuler un article existant, sans coût ni envoi de données à un tiers |
| API | Exposer l'agent : `/chat`, `/assist`, `/predict`, `/tickets`, `/feedback`, `/stats`, `/health` | FastAPI ([`api/main.py`](../../api/main.py)) | Schémas Pydantic validés à l'entrée, documentation `/docs` automatique, tests faciles avec `TestClient` |
| Interface | Conversation, suivi d'un ticket, statistiques, fichier de tickets | Streamlit, 4 onglets ([`ui/app.py`](../../ui/app.py)) | Interface en Python en quelques dizaines de lignes, suffisante pour la démonstration |
| Conteneur et intégration continue | Lancer API + interface en une commande ; vérifier chaque push | Docker, GitHub Actions ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)) | La CI existe déjà (ruff, mypy, pytest, couverture ≥ 95 %) ; Docker reste à écrire pour un déploiement reproductible |

**1.6 Hors périmètre** : messages dans une autre langue que l'anglais (orientés vers un humain, pas traduits) ; actions réelles sur le poste ou le compte de l'utilisateur (réinitialiser un mot de passe, redémarrer un service) ; authentification des utilisateurs et gestion des droits ; intégration à un vrai outil ITSM (GLPI, ServiceNow) ; réponse générée librement par un LLM sans article source ; pièces jointes et captures d'écran.

**1.7 Écart avec la fiche du catalogue.** Ajouts : la priorité de l'incident, l'abstention (`INDETERMINE` vers le tri N1) quand le modèle doute, le refus des messages hors sujet, et l'onglet fichier de tickets (F3). Modification : « répondre aux problèmes » se fait uniquement à partir d'articles validés et cités (recherche de type RAG, sans génération libre), pour qu'une procédure inventée ne puisse pas faire perdre des données. Retrait : aucun. Le cadrage détaillé est dans [`docs/cadrage/fiche-cadrage-projet.md`](../cadrage/fiche-cadrage-projet.md) et les fiches [`cas1`](../cadrage/cas1-escalade-incidents.md), [`cas2`](../cadrage/cas2-classement-incidents.md), [`cas3`](../cadrage/cas3-solutions-base-connaissances.md).

## Critères d'acceptation (vérifiés par le relecteur)

- [ ] Le problème et l'utilisateur sont compréhensibles sans le catalogue.
- [ ] Le nombre de fonctionnalités correspond à la taille de l'équipe.
- [ ] Chaque fonctionnalité est démontrable (pas de formulation vague comme « améliorer »).
- [ ] Chaque composant technique a une justification d'une ligne.
- [ ] Le hors périmètre est rempli.
