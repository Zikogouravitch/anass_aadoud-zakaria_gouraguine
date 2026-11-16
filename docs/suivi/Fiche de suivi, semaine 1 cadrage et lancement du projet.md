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
| Gouraguine Zakaria (membre B) |  |  |

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
| Cœur : modèle, agent ou chaîne RAG | scikit-learn (TF-IDF + MiniLM, LinearSVC calibré), recherche hybride d'articles, règles d'escalade ; | `src/train.py`, `src/predict.py`, `src/kb.py`, `api/tickets.py`, `api/conversation.py`, `models/support.joblib` (hors Git) |
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
| Origine des données (source, licence) |  |
| Volume disponible aujourd'hui |  |
| Format |  |
| Données personnelles : non, ou oui avec la méthode d'anonymisation |  |
| Jeu d'essai versionné dans le dépôt : chemin du fichier ou du script |  |

### Description du jeu de données

Décrivez le jeu de données tel qu'il est aujourd'hui, chiffres à l'appui. Chaque chiffre doit pouvoir être recalculé par un script du dépôt. Si votre projet n'utilise pas de tableau de données (agent, questions sur des documents), décrivez de la même façon votre corpus de documents ou votre jeu de cas d'évaluation.

Vue d'ensemble :

| Caractéristique | Votre réponse |
| --- | --- |
| Ce que représente une ligne (ou un document) |  |
| Nombre de lignes ou de documents |  |
| Nombre de variables (colonnes) |  |
| Période couverte et langue |  |
| Variable cible ou réponse attendue, s'il y en a une |  |
| Répartition de la cible : effectif par classe, ou minimum, moyenne et maximum |  |
| Pour un corpus de textes : longueur moyenne d'un document, en mots |  |
| Valeurs manquantes et doublons : nombre et traitement prévu |  |
| Découpage prévu : entraînement, test, évaluation |  |
| Script qui recalcule ces chiffres : chemin dans le dépôt |  |

Dictionnaire des variables (une ligne par colonne utilisée) :

| Variable | Type (texte, nombre, catégorie, date) | Signification | Exemple de valeur | Valeurs manquantes (%) |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

Trois exemples tirés du jeu de données :

| Exemple (entrée) | Réponse ou étiquette attendue | Nature de l'exemple : cas simple, cas difficile, cas limite |
| --- | --- | --- |
|  |  |  |
|  |  |  |
|  |  |  |

Limites connues du jeu de données (taille, déséquilibre entre classes, biais, données générées) :

## 6. Critères de réussite

Un critère est mesurable s'il a une valeur cible et une façon de la vérifier. Donnez-en trois ; la première ligne est un exemple à remplacer.

| Critère | Mesure | Valeur cible | Comment vous le vérifierez |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

## 7. Répartition et planning sur 3 semaines

Un livrable par semaine, repéré par un tag Git. Précisez ce que chaque livrable veut dire pour votre projet.

| Semaine | Livrable attendu | Pour votre projet, concrètement | Responsable | Tag |
| --- | --- | --- | --- | --- |
| 1 | Cadrage, dépôt initialisé, squelette exécutable |  |  | `s1` |
| 2 | Version minimale qui fonctionne de bout en bout |  |  | `s2` |
| 3 | Application finale, documentation, compte rendu |  |  | `v1.0.0` |

Répartition des responsabilités :

| Membre | Responsabilités sur les 3 semaines | Remplaçant en cas d'absence |
| --- | --- | --- |
| Aadoud Anass | Coordination et dépôt, prototype, schéma et écrans, `/chat`, onglet statistiques et `/stats`, Docker, démonstration (≈ 12 jours) | Gouraguine Zakaria |
| Gouraguine Zakaria |  |  |

## 8. Travail réalisé en semaine 1

Chaque membre remplit sa ligne lui-même. Le lien pointe vers ses commits ou sa pull request sur GitHub.

| Membre | Ce que j'ai fait cette semaine | Lien vers mes commits | Temps passé (heures) |
| --- | --- | --- | --- |
| Aadoud Anass | Livrable 1 (descriptif), livrable 3 (maquette, schéma Mermaid, 4 écrans), README de répartition, checklist de remise ; relecture des livrables 2 et 4 | [115e44b](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/115e44b), [a31cbc4](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/a31cbc4), [d3371c5](https://github.com/Zikogouravitch/anass_aadoud-zakaria_gouraguine/commit/d3371c5) | à compléter par le membre |
| Gouraguine Zakaria |  |  |  |

État du dépôt à la remise de la fiche :

- [ ] Dépôt créé, enseignant et tous les membres ajoutés (dépôt et deux membres : oui ; enseignant : à vérifier)
- [ ] README avec le titre, les membres, le sujet et les commandes d'installation (S1-1) (README seulement dans `docs/semaine1/` ; le README racine du code existe dans `Agent_support_info` mais le membre B y est « à compléter »)
- [x] Au moins un commit de chaque membre, depuis son propre compte (S1-2) (3 commits chacun dans le dépôt du groupe)
- [ ] `requirements.txt` installable sur un clone neuf, `.env.example` présent, aucun secret poussé (S1-3) (présents dans le code `Agent_support_info`, pas encore dans le dépôt du groupe)
- [ ] Squelette exécutable et au moins un test qui passe (S1-4) (en local : 491 tests passent, 1 échoue : `test_each_member_has_committed`, un seul auteur dans l'historique du code ; code à pousser dans le dépôt du groupe)
- [x] Jeu d'essai et schéma d'architecture dans le dépôt (S1-5) (`data/sample/`, `docs/semaine1/3-maquette.md`)
- [ ] Cette fiche poussée dans `docs/suivi/` et tag `s1` posé (S1-6)

## 9. Risques et points de blocage

| Risque ou blocage | Probabilité (faible, moyenne, forte) | Ce que vous ferez si cela arrive | Qui surveille |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
| Code développé dans un dépôt séparé (`Agent_support_info`, un seul auteur) et Docker encore absent : chemin critique T10 → T11 → T12 | Forte | Pousser le code dans le dépôt du groupe en semaine 2 ; écrire le Dockerfile dès que `/chat` et `/tickets` sont stables ; T10 ne dépasse pas 2 jours | Aadoud Anass |

Question à poser à l'enseignant, s'il y en a une : le code déjà développé pendant les TP (dépôt `Agent_support_info`) peut-il être importé tel quel dans le dépôt du groupe, ou faut-il reconstruire l'historique avec les commits de chaque membre ?

## 10. Engagements pour la semaine 2

Trois engagements au plus, chacun vérifiable dans le dépôt. Ils seront relus dans la fiche de la semaine 2.

| Engagement | Responsable | Comment on saura que c'est fait |
| --- | --- | --- |
| Code de l'agent dans le dépôt du groupe avec README racine, `requirements.txt`, `.env.example`, et `/chat` qui garde la conversation (T5) | Aadoud Anass | `pytest -q` vert sur `main` sur un clone neuf, `tests/test_chat.py` passe ; un incident résolu ne crée aucun ticket |
|  |  |  |
|  |  |  |

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
