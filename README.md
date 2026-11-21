# Agent_support_info

Agent de support informatique de premier niveau : l'employé décrit son incident en anglais, l'agent donne la catégorie, la priorité et une procédure citée de la base de connaissances, puis escalade vers un technicien (ticket pré-rempli) si le problème n'est pas résolu ou s'il est critique.

- **Sujet** : n° 9 du catalogue, *Agent de support informatique*
- **Membres** : Aadoud Anass (`anass0031`, coordinateur) · Gouraguine Zakaria (`Zikogouravitch`)
- **Dossier de cadrage** : [`docs/semaine1/`](docs/semaine1/README.md) · **Fiche de suivi** : [`docs/suivi/`](docs/suivi/)

## Installation

Python 3.11 ou plus récent.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Linux / macOS : source .venv/bin/activate
pip install -r requirements-dev.lock   # versions exactes testées
pip install -e . --no-deps
copy .env.example .env               # Linux / macOS : cp .env.example .env
```

### Dépendances

| Fichier | Rôle |
| --- | --- |
| `requirements.txt` / `requirements-dev.txt` | Ce dont le projet a besoin (versions minimales) : on les modifie à la main |
| `requirements.lock` / `requirements-dev.lock` | **Versions exactes** de tous les paquets, dépendances indirectes comprises, testées sur Python 3.11 (Windows, Linux, macOS) : on installe depuis ces fichiers |

Après une modification de `requirements*.txt`, régénérer les locks :

```powershell
uv pip compile requirements.txt --universal --python-version 3.11 --index-strategy unsafe-best-match --emit-index-url -o requirements.lock
uv pip compile requirements-dev.txt --universal --python-version 3.11 --index-strategy unsafe-best-match --emit-index-url -o requirements-dev.lock
```

`torch` est installé en version **CPU** (index PyTorch) : pas de CUDA, plus léger en CI et dans Docker.

## Vérifier

```powershell
pytest                # tests
ruff check .          # style
mypy support_agent    # types
```

## Données

```powershell
python -m support_agent.datasets.construire   # télécharge les 3 sources et construit data/processed/entrainement.csv
python -m support_agent.decrire               # recalcule les chiffres du jeu de données
```

Sources, licences et méthode d'étiquetage : [`docs/donnees.md`](docs/donnees.md).

## Modèle

```powershell
python -m support_agent.train                                   # ≈ 3 à 5 min sur CPU, écrit models/support.joblib + models/metrics.json
python -m support_agent.predict "My VPN keeps disconnecting"    # -> reseau + KB-NET-01
python -m support_agent.predict --json "The printer is offline"
```

Méthode et choix mesurés : [`docs/modele.md`](docs/modele.md).

## API et interface

```powershell
uvicorn support_agent.api.main:app --port 8000    # API : http://localhost:8000/docs (modèle préchargé en ~30 s)
streamlit run support_agent/ui/app.py             # interface : http://localhost:8501
```

| Route | Rôle |
| --- | --- |
| `GET /health` | État de l'API et du modèle (toujours ouverte) |
| `POST /predict` | Classement seul d'un message : catégorie, priorité, articles |
| `POST /chat` | Un tour de conversation : `{"message": "..."}` puis `{"conversation_id": "...", "action": "resolu" \| "non_resolu" \| "technicien" \| "confirmer_ticket" \| "annuler"}` ou une réponse libre |
| `POST /tickets` | Crée le ticket pré-rempli d'une conversation après confirmation : `{"conversation_id": "..."}` → `INC-00001` |
| `GET /tickets/{id}` | Suivi d'un ticket |
| `GET /tickets?statut=ouvert` | Liste pour les techniciens, cas critiques en tête |
| `PATCH /tickets/{id}` | Mise à jour par un technicien : `{"statut": "en_cours" \| "resolu" \| "ferme", "note": "..."}` |

Si `API_KEY` est rempli dans `.env`, chaque appel (sauf `/health`) doit envoyer l'en-tête `X-API-Key`.

Parcours d'une conversation : solution citée (essai 1) → article suivant (essai 2) → ticket pré-rempli proposé → créé après confirmation → identifiant affiché et suivi dans l'onglet « Track a ticket ». Un cas critique est escaladé tout de suite ; un message vague reçoit une question de précision ; un hors sujet est refusé poliment.

## Règles d'escalade

| Règle | Déclencheur | Motif du ticket |
| --- | --- | --- |
| R1 | Sécurité, panne de service, ou beaucoup de personnes touchées : escalade dès le 1er message | `cas_critique` |
| R2 | L'article dit qu'un technicien est **toujours** nécessaire (compte, remboursement…) | `article_exige_technicien` |
| R3 | 2 solutions essayées sans succès | `non_resolu_apres_essais` |
| R4 | L'employé demande un technicien | `demande_utilisateur` |
| R5 | Catégorie incertaine après la question de précision | `categorie_indeterminee` |

| Catégorie | Groupe qui reçoit le ticket |
| --- | --- |
| `securite` | Security team |
| `panne_service` | Operations |
| `compte_acces` | Identity & access |
| `facturation` | Billing |
| `reseau` | Network |
| `materiel` | Hardware & workplace |
| `logiciel` | Applications |
| indéterminée | Service desk N1 (triage) |

| Priorité | Délai annoncé |
| --- | --- |
| high (toujours pour un cas critique) | 4 hours |
| medium | 1 business day |
| low | 3 business days |

```powershell
python -m support_agent.bilan_tickets   # rejoue les 30 conversations de data/eval/conversations.json
```

## Mesures

```powershell
python -m support_agent.evaluer validation             # mesure de départ, répétable -> models/eval_validation.json
python -m support_agent.evaluer independant --final    # mesure finale : UNE seule lecture, tracée
```

| Fichier | Contenu |
| --- | --- |
| `models/metrics.json` | Test sur 20 % tenus à part, à l'entraînement |
| `models/eval_validation.json` | Mesure de départ : F1 macro, top-1, top-3, abstention, cas critiques, hors sujet, par classe, par difficulté, erreurs |
| `models/bilan_tickets.json` | Les 30 conversations : tickets créés et attendus |
| `models/independant_lu.json` | Trace de la lecture du jeu indépendant (après T12) |

Dernière mesure de départ (`jeu_validation.csv`, 120 messages) : F1 macro **0,917** · article top-1 **0,848** · top-3 **0,962** · cas critiques manqués **0/30** · hors sujet refusés 12/15 · 14 ms par message.

## Structure

| Dossier | Contenu |
| --- | --- |
| `support_agent/` | Cœur : configuration, données, modèle, base de connaissances, escalade |
| `support_agent/datasets/` | Téléchargement, étiquetage et fusion des sources (Tobi-Bueck, Super User, CLINC150) |
| `support_agent/api/` | API FastAPI (`/health`, `/predict`, `/chat`, `/tickets`) |
| `support_agent/escalade.py`, `tickets.py` | Règles d'escalade, tickets (création, suivi) |
| `support_agent/ui/` | Interface Streamlit (onglets Chat et Track a ticket) et client HTTP |
| `data/sample/` | Jeu d'essai versionné (100 tickets, 57 articles, 20 cas du jeu d'or) |
| `data/eval/` | Jeux d'évaluation écrits à la main : validation (120) et indépendant (126) |
| `tests/` | Tests pytest |
| `docs/` | Cadrage (semaine 1) et fiches de suivi |

Les modèles entraînés (`models/*.joblib`), les tickets créés (`tickets/`) et le fichier `.env` ne sont jamais versionnés.
