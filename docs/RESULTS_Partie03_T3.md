# Résultats — Partie 03 (T3 : entraînement du modèle et prototype)

## Tests et qualité du code

| Outil | Résultat |
| --- | --- |
| `pytest` | **75 passed** |
| Couverture | **99 %** (669 instructions) |
| `ruff` | All checks passed |
| `mypy` | Success: no issues found in 24 source files |

## Comparaison des modèles de classement (`jeu_validation.csv`, 120 messages)

| Configuration | F1 macro | Exactitude |
| --- | --- | --- |
| TF-IDF seul | 0,626 | 0,642 |
| TF-IDF + symptômes de la base | 0,844 | 0,842 |
| TF-IDF + base, poids Tobi × 0,5 | 0,868 | 0,867 |
| MiniLM seul + base | 0,804 | 0,800 |
| MiniLM seul + base, poids Tobi × 0,5 | 0,822 | 0,817 |
| TF-IDF + MiniLM + base (poids Tobi 0,3 / 0,6 / 1,0) | 0,892 / 0,901 / **0,909** | 0,892 / 0,900 / 0,908 |
| TF-IDF + MiniLM × 2 + base | 0,901 – 0,909 | 0,900 – 0,908 |
| TF-IDF + MiniLM × 3 + base | 0,879 | 0,875 |

Retenu : **TF-IDF + MiniLM + symptômes de la base**, sans poids sur les sources.

## Réglage du classifieur calibré

| C | F1 macro |
| --- | --- |
| 0,3 | 0,901 |
| 0,5 | 0,893 |
| **1,0** | **0,909** |

| Seuil d'abstention (C = 1) | Abstention | Exactitude des réponses données | Erreurs non abstenues |
| --- | --- | --- | --- |
| 0,40 | 4,2 % | 0,913 | 10 |
| **0,50** | **9,2 %** | **0,927** | 8 |
| 0,60 (valeur de la fiche 1) | 20,0 % | 0,927 | 7 |

## Comparaison des méthodes de recherche d'article

| Méthode | Top-1 | Top-3 |
| --- | --- | --- |
| TF-IDF | 0,533 | 0,819 |
| TF-IDF + probabilité de catégorie | 0,619 | 0,857 |
| MiniLM | 0,838 | 0,952 |
| MiniLM + TF-IDF | 0,800 | 0,952 |
| Restriction à la catégorie prédite | 0,838 | 0,914 |
| **MiniLM + 0,1 × probabilité de catégorie** | **0,848** | **0,962** |

## Modèle final : test sur 20 % tenus à part (`models/metrics.json`)

| Mesure | Valeur |
| --- | --- |
| Lignes d'entraînement | 10 721 |
| F1 macro | **0,89** |
| Exactitude | 0,892 |
| Abstention | 6 % |

| Source | Exactitude |
| --- | --- |
| Super User | 0,901 |
| Tobi-Bueck | 0,866 |
| Stack Exchange | 0,851 |
| CLINC150 | 1,000 |

## Effet des règles de sécurité (validation)

| Mesure | Modèle seul | + règles (vague, hors sujet douteux, cas étendus, banque exclue de CLINC) | Objectif fiche |
| --- | --- | --- | --- |
| F1 macro | 0,918 | **0,917** | ≥ 0,85 ✔ |
| Bon article top-1 | 0,829 | **0,848** | ≥ 0,75 ✔ |
| Bon article top-3 | 0,943 | **0,962** | ≥ 0,90 ✔ |
| Cas critiques manqués | 3 / 30 | **0 / 30** | ≤ 1 ✔ |
| Hors sujet refusés | 13 / 15 | 12 / 15 | ≥ 90 % ✗ |

## Progression du F1 macro (validation)

| Étape | F1 macro |
| --- | --- |
| Tobi-Bueck seul | 0,389 |
| + données réelles | 0,696 |
| + symptômes de la base | 0,844 |
| + MiniLM | 0,909 |
| + réglages | 0,917 |

## Prototype (`python -m support_agent.predict`)

| Message | Catégorie | Article |
| --- | --- | --- |
| My VPN keeps disconnecting | `reseau` (0,95) | KB-NET-01 |
| I clicked a link in an email and typed my password | `securite` (0,79), critique | KB-SEC-01 |
| Nobody in the company can open the ERP | `panne_service`, critique | KB-OUT-06 |
| We were charged twice this month | `facturation` (0,81) | KB-BIL-01 |
| Can you book a table for two tonight? | `hors_sujet` | — |
| It does not work | `INDETERMINE` (vague) | — |
