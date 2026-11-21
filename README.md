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

## Structure

| Dossier | Contenu |
| --- | --- |
| `support_agent/` | Cœur : configuration, données, modèle, base de connaissances, escalade |
| `support_agent/datasets/` | Téléchargement, étiquetage et fusion des sources (Tobi-Bueck, Super User, CLINC150) |
| `data/sample/` | Jeu d'essai versionné (100 tickets, 57 articles, 20 cas du jeu d'or) |
| `data/eval/` | Jeux d'évaluation écrits à la main : validation (120) et indépendant (126) |
| `tests/` | Tests pytest |
| `docs/` | Cadrage (semaine 1) et fiches de suivi |

Les modèles entraînés (`models/*.joblib`), les tickets créés (`tickets/`) et le fichier `.env` ne sont jamais versionnés.
