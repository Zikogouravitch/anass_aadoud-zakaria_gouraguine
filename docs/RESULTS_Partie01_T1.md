# Résultats — Partie 01 (T1 : squelette exécutable)

## Tests et qualité du code

Python 3.11, environnement installé depuis `requirements-dev.lock`.

| Outil | Résultat |
| --- | --- |
| `pytest` | **18 passed** (13 squelette + 5 fiches de cadrage) |
| Couverture (`support_agent`) | **100 %** (64 instructions) |
| `ruff check .` | All checks passed |
| `mypy support_agent tests` | Success: no issues found in 6 source files |

## Ce que les tests vérifient

| Vérification | Résultat |
| --- | --- |
| Échantillon `tobi_bueck_extrait.csv` | 100 lignes, 7 catégories présentes |
| Base de connaissances | 57 articles, 7 catégories, `KB-NET-01` présent avec ses étapes |
| Jeu d'or | 20 lignes |
| Taille de `data/sample/` | < 10 Mo |
| Fichiers mal formés (colonne manquante, catégorie ou priorité inconnue, article en double, fichier absent) | Erreur claire levée |
| Secrets | `.env` ignoré par Git, `.env.example` sans clé |
| Fiches de cadrage (`docs/cadrage/`) | 3 fiches complètes, une approche cochée par fiche, au moins 2 critères cités |

## Dépendances (lock)

| Fichier | Paquets épinglés |
| --- | --- |
| `requirements.lock` | 54 |
| `requirements-dev.lock` | 67 |
