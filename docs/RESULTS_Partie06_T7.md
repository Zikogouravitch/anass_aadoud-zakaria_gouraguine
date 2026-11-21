# Résultats — Partie 06 (T7 : mesure de départ sur la validation)

## Tests et qualité du code

| Outil | Résultat |
| --- | --- |
| `pytest` | **165 passed** |
| Couverture | **99 %** (1 563 instructions) |
| `ruff` | All checks passed |
| `mypy` | Success: no issues found in 41 source files |

## Mesure de départ (`python -m support_agent.evaluer validation` → `models/eval_validation.json`)

`jeu_validation.csv`, 120 messages, vrai modèle.

| Mesure | Valeur | Objectif fiche |
| --- | --- | --- |
| **F1 macro** | **0,917** | ≥ 0,85 ✔ |
| Exactitude | 0,917 | — |
| **Bon article en top-1** | **0,848** | ≥ 0,75 ✔ |
| **Bon article en top-3** | **0,962** | ≥ 0,90 ✔ |
| Cas critiques manqués | **0 / 30** | ≤ 1 ✔ |
| Hors sujet refusés | 12 / 15 = 80 % (refus à tort : 0) | ≥ 90 % ✗ |
| Abstention (`INDETERMINE`) | 8,3 % | — |
| Exactitude des réponses données | 0,936 | — |
| F1 macro en comptant l'abstention comme une erreur | 0,895 | — |
| Temps moyen par message | 13,7 ms (CPU) | — |

## Par classe

| Classe | F1 |
| --- | --- |
| `securite` | 0,968 |
| `facturation` | 0,968 |
| `panne_service` | 0,929 |
| `reseau` | 0,929 |
| `compte_acces` | 0,903 |
| `logiciel` | 0,897 |
| `hors_sujet` | 0,889 |
| `materiel` | 0,857 |

## Par difficulté

| Difficulté | Exactitude |
| --- | --- |
| Simple | 0,97 |
| Texte court | 1,00 |
| Texte vague | 1,00 |
| Vocabulaire partagé | 0,50 |
| Négation | 0,50 |

## Les 10 erreurs

| Message | Attendu | Prédit |
| --- | --- | --- |
| My H: drive disappeared from File Explorer | `reseau` | `materiel` |
| My mouse is fine, the real issue is that the Wi-Fi… | `reseau` | `materiel` |
| I lost access to my email after changing my phone number for MFA | `compte_acces` | `securite` |
| Outlook keeps asking me for my password again and again | `logiciel` | `compte_acces` |
| In Zoom people can't hear me although my headset works… | `logiciel` | `materiel` |
| No one can log in this morning | `panne_service` | `compte_acces` (reste marqué critique) |
| Customers cannot pay on our online shop | `panne_service` | `facturation` (reste marqué critique) |
| The coffee machine in the kitchen is leaking | `hors_sujet` | `materiel` |
| My car makes a strange noise when braking | `hors_sujet` | `materiel` |
| The air conditioning in meeting room B is too cold | `hors_sujet` | `logiciel` |

## Protection du jeu indépendant

| Commande | Résultat |
| --- | --- |
| `evaluer independant` | Refusé : `--final` exigé |
| 1re lecture avec `--final` | Autorisée et tracée dans `models/independant_lu.json` |
| 2e lecture | Refusée, sauf `--relire`, qui est tracée aussi |
