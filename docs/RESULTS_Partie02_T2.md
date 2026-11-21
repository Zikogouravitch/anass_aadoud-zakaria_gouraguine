# Résultats — Partie 02 (T2 : données d'entraînement et jeux d'évaluation)

## Tests et qualité du code

| Outil | Résultat |
| --- | --- |
| `pytest` | **46 passed** |
| Couverture | **100 %** (363 instructions) |
| `ruff` | All checks passed |
| `mypy` | Success: no issues found in 16 source files |

## Jeu d'entraînement construit (`python -m support_agent.datasets.construire`)

| Étape | Lignes |
| --- | --- |
| Tobi-Bueck (incidents en anglais, étiquetés) | 13 849 |
| Super User + Stack Exchange (titres d'incidents) | 3 535 |
| CLINC150 (hors sujet) | 1 452 |
| Après retrait des doublons | 16 587 |
| Retirés par l'anti-fuite (trop proches d'un texte d'évaluation) | 9 |
| **Jeu final** (après plafond de 1 200 Tobi par catégorie) | **10 680** |

| Catégorie | Lignes |
| --- | --- |
| `logiciel` | 2 012 |
| `reseau` | 1 695 |
| `securite` | 1 627 |
| `hors_sujet` | 1 444 |
| `panne_service` | 1 200 |
| `materiel` | 1 112 |
| `facturation` | 897 |
| `compte_acces` | 693 |

| Source | Lignes | Mots par message (moyenne) |
| --- | --- | --- |
| Tobi-Bueck (généré) | 5 785 | 60,5 |
| Super User (réel) | 2 695 | 10,0 |
| CLINC150 (réel) | 1 444 | 8,6 |
| Stack Exchange (réel) | 756 | 10,9 |

## Jeux d'évaluation (`python -m support_agent.decrire`)

| Jeu | Lignes | Mots par message | Composition | Critiques |
| --- | --- | --- | --- | --- |
| `jeu_validation.csv` | 120 | 9,3 | 15 × 7 catégories + 15 hors sujet | 30 |
| `jeu_independant.csv` | 126 | 8,6 | 16 × 7 catégories + 14 hors sujet | 32 |
| Échantillon Tobi-Bueck | 100 | 62,8 | 14–15 par catégorie | — |

## Comparaison : l'apport des données réelles

Même modèle simple (TF-IDF mots + caractères, LinearSVC), aucun réglage, mesuré sur `jeu_validation.csv`.

| Entraîné sur | F1 macro | Exactitude |
| --- | --- | --- |
| Tobi-Bueck seul (7 catégories) | 0,389 | 0,438 |
| **Tobi-Bueck + Super User + Stack Exchange** (7 catégories) | **0,696** | 0,705 |
| 3 sources, 8 classes (avec `hors_sujet`) | 0,626 | 0,642 |

Les données réelles et courtes font gagner **+31 points** de F1 sur des messages de chat.
