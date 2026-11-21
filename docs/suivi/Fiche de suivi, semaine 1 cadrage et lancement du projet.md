# Fiche de suivi, semaine 1 : cadrage et lancement du projet

Nov 16, 2026 · @Larhlimi

## Mode d'emploi

Cette fiche fixe votre projet et prouve que le groupe a démarré : elle compte pour 5 points sur 100. Les fiches des semaines 2 et 3 comptent chacune pour 10 points.

- Une seule fiche par groupe, remplie ensemble et relue par chaque membre.
- Dépôt de la fiche : `docs/suivi/fiche-semaine-1.md` dans le dépôt GitHub du groupe (push S1-6 de la liste des push).
- Date limite : fin de la semaine 1 du projet, à la date annoncée en séance.
- Réponses courtes et vérifiables : un chiffre, un lien ou un nom de fichier valent mieux qu'une phrase générale.
- Si un point n'est pas encore tranché, écrivez « à décider » et la date de décision, plutôt que de laisser la case vide.

Rappel du barème du projet, sur 100 : application finale 20, dépôt GitHub 20, fiches hebdomadaires 25 (5 + 10 + 10), soutenance 20, compte rendu 15.

## 1. Identification du groupe

| Élément | Votre réponse |
| --- | --- |
| Nom du groupe | Aadoud Anass & Gouraguine Zakaria |
| Titre du projet | Agent_support_info : agent de support informatique de premier niveau |
| Sujet : numéro du catalogue, ou « hors catalogue » | Sujet 9 du catalogue, *Agent de support informatique* |
| Adresse du dépôt GitHub | https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine |
| Enseignant ajouté au dépôt (oui ou non) | oui |
| Date de remise de la fiche | 16/11/2026 |

Membres du groupe (2 à 4 lignes) :

| Nom et prénom | Compte GitHub | Rôle principal dans le projet |
| --- | --- | --- |
| Aadoud Anass (membre A, coordinateur) | anass0031 | Descriptif (L1), maquette et architecture (L3), API `/chat`, interface Streamlit, Docker |
| Gouraguine Zakaria (membre B) | Zikogouravitch | Dataset (L2), pipeline (L4), règles d'escalade et tickets, évaluation, CI |

## 2. Sujet et besoin

| Question | Votre réponse |
| --- | --- |
| Besoin en une phrase | Les techniciens de niveau 1 perdent leur temps à trier les incidents et à redonner les mêmes procédures simples, ce qui retarde les cas critiques (sécurité, panne générale). |
| Utilisateur final : qui se sert de l'application | L'employé qui rencontre un incident (principal) ; le technicien qui reçoit les tickets escaladés (secondaire). |
| Ce que fait l'application, vu par l'utilisateur (3 lignes au plus) | L'employé décrit son incident en anglais ; l'agent affiche la catégorie, la priorité et une procédure pas à pas citée (ex. `KB-NET-01`). S'il n'est pas résolu après deux essais, sur demande ou pour un cas critique, l'agent propose un ticket pré-rempli vers le bon groupe, créé après confirmation et suivi par son identifiant. |
| Approche retenue (règles, apprentissage, RAG, agent) et raison du choix | Apprentissage (TF-IDF mots + caractères + all-MiniLM-L6-v2, LinearSVC calibré, abstention sous 0,60) + recherche de type RAG sans génération libre sur 57 articles validés + règles d'escalade. Données étiquetées disponibles, réponse en ~0,1 s sans GPU, résultat mesurable ; une procédure inventée par un LLM pourrait faire perdre des données. |
| Conséquence d'une erreur de l'application, et validation humaine prévue | Mauvaise procédure (temps perdu) ou cas critique non escaladé (risque de sécurité). Garde-fous : abstention (`INDETERMINE` → tri N1 humain), cas critiques escaladés tout de suite, ticket créé seulement après confirmation de l'employé, traité ensuite par un technicien. |
| Sujet hors catalogue : projet du catalogue auquel il est comparable | Sans objet (sujet 9 du catalogue). |

## 3. Périmètre

La version minimale est le parcours complet le plus simple, de la demande de l'utilisateur jusqu'à la réponse affichée. Elle doit fonctionner à la fin de la semaine 2.

| Rubrique | Votre réponse |
| --- | --- |
| Version minimale : le parcours que vous montrerez en semaine 2 | Onglet Chat : « My VPN keeps disconnecting every 10 minutes » → `/chat` → catégorie `reseau`, priorité, étapes de `KB-NET-01` → « pas résolu » deux fois → ticket pré-rempli confirmé → identifiant affiché. |
| Fonction 1, indispensable | F1 : classement de l'incident et proposition de solution citée dans une conversation ; hors sujet refusé poliment. |
| Fonction 2, indispensable | F2 : escalade et ticket pré-rempli (catégorie, priorité, groupe, motif, articles essayés), créé après confirmation, suivi par identifiant. |
| Fonction 3, si le temps le permet | F3 : traitement d'un fichier CSV de tickets (tri, cas critiques en tête) et page de statistiques (tickets par catégorie, taux de résolution, avis). |
| Hors périmètre : ce que vous ne ferez pas | Autres langues que l'anglais ; actions réelles sur le poste ou le compte ; authentification et droits ; intégration à un outil ITSM (GLPI, ServiceNow) ; réponse générée librement par un LLM sans article source ; pièces jointes et captures d'écran. |

## 4. Architecture et technologies

| Composant | Choix prévu | Dossier ou fichier dans le dépôt |
| --- | --- | --- |
| Cœur : modèle, agent ou chaîne RAG | scikit-learn (TF-IDF + MiniLM, LinearSVC calibré), recherche hybride d'articles, règles d'escalade ; Ollama llama3.2 en option (reformulation, désactivé par défaut) | `src/train.py`, `src/predict.py`, `src/kb.py`, `api/tickets.py`, `api/conversation.py`, `models/support.joblib` (hors Git) |
| API | FastAPI : `/chat`, `/assist`, `/predict`, `/tickets`, `/feedback`, `/stats`, `/health` | `api/main.py`, `api/schemas.py` |
| Interface | Streamlit, 4 onglets (Chat, Track a ticket, Statistics, A file of tickets) | `ui/app.py`, `ui/client.py`, `ui/fichier.py` |
| Données et stockage | CSV versionnés (base de 57 articles, jeux d'évaluation) ; tickets, conversations et avis en JSON Lines hors Git | `data/`, `data/sample/`, `tickets/` (ignoré) |
| Tests | pytest + ruff + mypy, couverture ≥ 95 % en CI (GitHub Actions) | `tests/`, `.github/workflows/ci.yml` |
| Services externes et clés nécessaires | Hugging Face (téléchargement de Tobi-Bueck, sans clé) ; Ollama local en option ; `API_KEY` de l'API dans `.env` (modèle : `.env.example`) | `.env.example` |

Joignez un schéma d'architecture au dépôt (`docs/architecture.png`, ou un diagramme Mermaid dans le README) et indiquez son lien ici : [`docs/semaine1/3-maquette.md`](../semaine1/3-maquette.md) (diagramme Mermaid, section 3.1).

## 5. Données

Règle du cours : uniquement des données publiques, fictives ou anonymisées.

| Question | Votre réponse |
| --- | --- |
| Origine des données (source, licence) | (1) `Tobi-Bueck/customer-support-tickets` sur Hugging Face, tickets fictifs générés, licence CC BY-NC 4.0 ; (2) base de connaissances et jeux d'évaluation rédigés par le binôme d'après les pages publiques Microsoft Support (source citée). |
| Volume disponible aujourd'hui | Tobi-Bueck : 61 765 tickets, 11 213 incidents en anglais, 8 452 gardés après nettoyage ; base : 57 articles ; évaluation : 20 + 120 + 126 incidents et 30 conversations ; démonstration : 1 840 lignes. Échantillon `data/sample/` : 100 + 57 + 20 lignes, 78 Ko. |
| Format | Parquet (Tobi-Bueck, 24 Mo) ; CSV (base, jeux d'évaluation, échantillon) ; JSON Lines (tickets, conversations, avis). |
| Données personnelles : non, ou oui avec la méthode d'anonymisation | Non : tickets fictifs et incidents écrits par le binôme ; les saisies de démonstration restent hors Git (`tickets/` ignoré) et ne sont envoyées à aucun tiers. |
| Jeu d'essai versionné dans le dépôt : chemin du fichier ou du script | `data/sample/tobi_bueck_extrait.csv`, `data/sample/base_connaissances.csv`, `data/sample/jeu_or.csv` ; jeu complet régénérable par `src/make_demo.py`. |

### Description du jeu de données

Décrivez le jeu de données tel qu'il est aujourd'hui, chiffres à l'appui. Chaque chiffre doit pouvoir être recalculé par un script du dépôt. Si votre projet n'utilise pas de tableau de données (agent, questions sur des documents), décrivez de la même façon votre corpus de documents ou votre jeu de cas d'évaluation.

Chiffres ci-dessous recalculés le 16/11/2026 sur l'échantillon `data/sample/tobi_bueck_extrait.csv` (jeu d'entraînement) ; jeu complet entre parenthèses.

Vue d'ensemble :

| Caractéristique | Votre réponse |
| --- | --- |
| Ce que représente une ligne (ou un document) | Un incident informatique en anglais (sujet + corps du ticket), avec sa catégorie IT et sa priorité. |
| Nombre de lignes ou de documents | 100 dans l'échantillon (8 452 dans le jeu nettoyé complet) ; base : 57 articles ; jeu d'or : 20 incidents. |
| Nombre de variables (colonnes) | 3 dans l'échantillon (`text`, `categorie`, `priorite`) ; 7 dans la base ; 4 dans le jeu d'or. |
| Période couverte et langue | Anglais ; tickets non datés (jeu généré) ; base rédigée en novembre 2026. |
| Variable cible ou réponse attendue, s'il y en a une | `categorie` (7 classes IT ; + `hors_sujet` dans le jeu de démonstration) ; cible secondaire `priorite` (low, medium, high). |
| Répartition de la cible : effectif par classe, ou minimum, moyenne et maximum | Échantillon : `reseau` 15, `panne_service` 15, `materiel` 14, `logiciel` 14, `facturation` 14, `compte_acces` 14, `securite` 14 ; priorité : medium 40, high 38, low 22. Jeu complet déséquilibré : `logiciel` 2 868, `securite` 2 229 … `compte_acces` 374, `facturation` 269. |
| Pour un corpus de textes : longueur moyenne d'un document, en mots | 62,8 mots (échantillon) ; 60 mots (jeu complet) ; 10,9 mots dans le jeu d'or (messages courts). |
| Valeurs manquantes et doublons : nombre et traitement prévu | Échantillon : 0 manquante, 0 doublon (doublons retirés au nettoyage de `src/train.py`). Base : 0 manquante sauf `source` (31 sur 57, 54,4 %) à compléter. Jeu d'or : `difficulte` vide = cas simple (10 sur 20). |
| Découpage prévu : entraînement, test, évaluation | Entraînement / test 80 / 20 sur le jeu de démonstration (1 472 / 368) ; réglage sur `jeu_validation.csv` (120) ; mesure finale une seule fois sur `jeu_independant.csv` (126). |
| Script qui recalcule ces chiffres : chemin dans le dépôt | `src/train.py` (nettoyage, `models/metrics.json`) et `src/evaluer.py` ; script de description de l'échantillon `src/decrire_donnees.py` à ajouter (engagement semaine 2). |

Dictionnaire des variables (une ligne par colonne utilisée) :

| Variable | Type (texte, nombre, catégorie, date) | Signification | Exemple de valeur | Valeurs manquantes (%) |
| --- | --- | --- | --- | --- |
| `text` | texte | Description de l'incident (sujet + corps) | « My VPN keeps disconnecting every 10 minutes when I work from home » | 0 |
| `categorie` | catégorie (7 classes) | Catégorie IT de l'incident, déduite des tags | `reseau` | 0 |
| `priorite` | catégorie (low, medium, high) | Priorité du ticket | `medium` | 0 |
| `id` / `titre` / `etapes` (base) | texte | Référence, titre et étapes (séparées par `\|`) de l'article de solution | `KB-SEC-01`, « Suspicious or phishing email » | 0 |
| `escalade_si` (base) | texte | Condition qui impose l'escalade vers un technicien | « you clicked the link or entered your credentials » | 0 |

Trois exemples tirés du jeu de données :

| Exemple (entrée) | Réponse ou étiquette attendue | Nature de l'exemple : cas simple, cas difficile, cas limite |
| --- | --- | --- |
| « My VPN keeps disconnecting every 10 minutes when I work from home » (`jeu_or.csv`) | `reseau`, article `KB-NET-01` | Cas simple |
| « I can't log in, my account is locked after too many password attempts » (`jeu_or.csv`) | `compte_acces` | Cas simple |
| « A financial organization encountered delays in data processing… compatibility problems between software and hardware… » (`tobi_bueck_extrait.csv`) | `materiel`, priorité `low` | Cas difficile (texte long, vocabulaire partagé logiciel / matériel) |

Limites connues du jeu de données (taille, déséquilibre entre classes, biais, données générées) : tickets Tobi-Bueck générés et longs (courriels), loin des messages courts d'une conversation ; catégorie déduite des tags, non fournie ; priorités incohérentes (50 % de priorité exacte seulement en apprenant dessus) ; déséquilibre fort entre classes ; fuite repérée sur le jeu de démonstration (94 % des phrases de test partageaient leur symptôme avec l'entraînement), d'où les jeux de validation et indépendant écrits à part.

## 6. Critères de réussite

Un critère est mesurable s'il a une valeur cible et une façon de la vérifier. Donnez-en trois ; la première ligne est un exemple à remplacer.

| Critère | Mesure | Valeur cible | Comment vous le vérifierez |
| --- | --- | --- | --- |
| Classement correct des incidents | F1 macro sur le jeu indépendant (126 messages) | ≥ 0,85 | `python src/evaluer.py independant` (lu une seule fois) ; départ sur la démonstration : 0,948 (`models/metrics.json`) |
| Bonne solution proposée | Part des incidents dont un article attendu (`articles_ok`) est en top-1 / top-3 | ≥ 75 % / ≥ 90 % | `src/evaluer_articles.py` sur `jeu_validation.csv` puis `jeu_independant.csv` |
| Escalade sûre | Cas critiques manqués sur 32 ; hors sujet refusés sur 14 ; tickets sur les 30 conversations | ≤ 1 manqué ; ≥ 90 % refusés ; 10 tickets, tous attendus | `src/bilan_tickets.py`, `tests/test_escalade.py` |

## 7. Répartition et planning sur 3 semaines

Un livrable par semaine, repéré par un tag Git. Précisez ce que chaque livrable veut dire pour votre projet.

| Semaine | Livrable attendu | Pour votre projet, concrètement | Responsable | Tag |
| --- | --- | --- | --- | --- |
| 1 | Cadrage, dépôt initialisé, squelette exécutable | Dossier de lancement fusionné (L1 à L4), `data/sample/`, schéma Mermaid et 4 maquettes, prototype `python src/predict.py "My VPN keeps disconnecting"` → `reseau` + `KB-NET-01` (T1 à T4) | Anass (coordination), Zakaria | `s1` |
| 2 | Version minimale qui fonctionne de bout en bout | `/chat` avec tentatives et question de précision, règles d'escalade et `/tickets`, mesure de départ sur la validation (T5 à T7) | Anass (T5), Zakaria (T6, T7) | `s2` |
| 3 | Application finale, documentation, compte rendu | Onglets fichier et statistiques, Docker + CI au vert, mesure finale sur le jeu indépendant, README et compte rendu (T8 à T13) | Anass (T9, T10, démo), Zakaria (T8, T11, T12, rapport des mesures) | `v1.0.0` |

Répartition des responsabilités :

| Membre | Responsabilités sur les 3 semaines | Remplaçant en cas d'absence |
| --- | --- | --- |
| Aadoud Anass | Coordination et dépôt, prototype, schéma et écrans, `/chat`, onglet statistiques et `/stats`, Docker, démonstration (≈ 12 jours) | Gouraguine Zakaria |
| Gouraguine Zakaria | Données et échantillon, pipeline, escalade et tickets, mesures (départ et finale), onglet fichier et `/assist`, CI, rapport des mesures (≈ 12 jours) | Aadoud Anass |

## 8. Travail réalisé en semaine 1

Chaque membre remplit sa ligne lui-même. Le lien pointe vers ses commits ou sa pull request sur GitHub.

| Membre | Ce que j'ai fait cette semaine | Lien vers mes commits | Temps passé (heures) |
| --- | --- | --- | --- |
| Aadoud Anass | Livrable 1 (descriptif), livrable 3 (maquette, schéma Mermaid, 4 écrans), README de répartition, checklist de remise ; relecture des livrables 2 et 4 | [115e44b](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/115e44b), [a31cbc4](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/a31cbc4), [d3371c5](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/d3371c5) | à compléter par le membre |
| Gouraguine Zakaria | Création du dépôt, livrable 2 (dataset, `data/sample/`), livrable 4 (pipeline des tâches) ; relecture des livrables 1 et 3 | [55e9488](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/55e9488), [f0c8f73](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/f0c8f73), [0075f81](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/0075f81) | à compléter par le membre |

État du dépôt à la remise de la fiche :

- [x] Dépôt créé, enseignant et tous les membres ajoutés (dépôt et deux membres : oui ; enseignant : à vérifier)
- [x] README avec le titre, les membres, le sujet et les commandes d'installation (S1-1) (README seulement dans `docs/semaine1/` ; le README racine du code existe dans `Agent_support_info` mais le membre B y est « à compléter »)
- [x] Au moins un commit de chaque membre, depuis son propre compte (S1-2) (3 commits chacun dans le dépôt du groupe)
- [x] `requirements.txt` installable sur un clone neuf, `.env.example` présent, aucun secret poussé (S1-3) (présents dans le code `Agent_support_info`, pas encore dans le dépôt du groupe)
- [x] Squelette exécutable et au moins un test qui passe (S1-4) 
- [x] Jeu d'essai et schéma d'architecture dans le dépôt (S1-5) (`data/sample/`, `docs/semaine1/3-maquette.md`)
- [x] Cette fiche poussée dans `docs/suivi/` et tag `s1` posé (S1-6)

## 9. Risques et points de blocage

| Risque ou blocage | Probabilité (faible, moyenne, forte) | Ce que vous ferez si cela arrive | Qui surveille |
| --- | --- | --- | --- |
| Tobi-Bueck inaccessible ou trop éloigné des messages courts d'une conversation | Moyenne | Repli sur le jeu synthétique de `src/make_demo.py` (1 840 lignes, sans réseau, déjà utilisé en CI) ; mesure sur nos jeux de validation et indépendant | Gouraguine Zakaria |
| Cas critique (sécurité, panne générale) non escaladé ou ticket créé à tort | Moyenne | Règles d'escalade testées une à une (`tests/test_escalade.py`), bilan sur les 30 conversations ; abaisser le seuil des cas critiques | Gouraguine Zakaria |
| Code développé dans un dépôt séparé (`Agent_support_info`, un seul auteur) et Docker encore absent : chemin critique T10 → T11 → T12 | Forte | Pousser le code dans le dépôt du groupe en semaine 2 ; écrire le Dockerfile dès que `/chat` et `/tickets` sont stables ; T10 ne dépasse pas 2 jours | Aadoud Anass |

Question à poser à l'enseignant, s'il y en a une : le code déjà développé pendant les TP (dépôt `Agent_support_info`) peut-il être importé tel quel dans le dépôt du groupe, ou faut-il reconstruire l'historique avec les commits de chaque membre ?

## 10. Engagements pour la semaine 2

Trois engagements au plus, chacun vérifiable dans le dépôt. Ils seront relus dans la fiche de la semaine 2.

| Engagement | Responsable | Comment on saura que c'est fait |
| --- | --- | --- |
| Code de l'agent dans le dépôt du groupe avec README racine, `requirements.txt`, `.env.example`, et `/chat` qui garde la conversation (T5) | Aadoud Anass | `pytest -q` vert sur `main` sur un clone neuf, `tests/test_chat.py` passe ; un incident résolu ne crée aucun ticket |
| Règles d'escalade et ticket pré-rempli via `/tickets` (T6) | Gouraguine Zakaria | `tests/test_escalade.py` vert ; les 30 conversations donnent 10 tickets, tous attendus |
| Mesure de départ sur la validation (T7) et script de description des données | Gouraguine Zakaria | `python src/evaluer.py validation` écrit un JSON avec F1 macro, top-1 et top-3 ; tag `s2` posé |

## Cadre réservé à l'enseignant

| Rubrique | Barème | Note |
| --- | --- | --- |
| Cadrage : sujet, périmètre, critères mesurables (rubriques 2, 3 et 6) | 2 |  |
| Organisation : architecture, données, rôles, planning (rubriques 4, 5 et 7) | 1 |  |
| Preuves GitHub de la semaine 1, contribution de chaque membre (rubrique 8) | 1,5 |  |
| Risques et engagements pour la semaine 2 (rubriques 9 et 10) | 0,5 |  |
| **Total** | **5** |  |

Décision : sujet validé, ou fiche à reprendre avant le :

Commentaire :
