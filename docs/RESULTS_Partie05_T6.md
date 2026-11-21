# Résultats — Partie 05 (T6 : règles d'escalade et tickets)

## Tests et qualité du code

| Outil | Résultat |
| --- | --- |
| `pytest` | **159 passed** |
| Couverture | **99 %** (1 467 instructions) |
| `ruff` | All checks passed |
| `mypy` | Success: no issues found in 39 source files |

## Bilan des 30 conversations (`python -m support_agent.bilan_tickets`, vrai modèle)

```
10 tickets créés / 10 attendus · 10 corrects · 0 en trop · 0 manqués · conversations conformes 29/30
```

| Groupe de conversations | Nombre | Conformes | Résultat |
| --- | --- | --- | --- |
| 2 échecs puis ticket | 3 | 3 | `reseau`, `materiel`, `logiciel` · `non_resolu_apres_essais` |
| Cas critiques | 3 | 3 | `securite` ×2, `panne_service` · `cas_critique` |
| Demande de technicien | 1 | 1 | `materiel` · `demande_utilisateur` |
| Article « always » | 2 | 2 | `compte_acces`, `facturation` · `article_exige_technicien` |
| Indéterminé après précision | 1 | 1 | tri N1 · `categorie_indeterminee` |
| Résolu à l'essai 1 | 8 | 8 | aucun ticket |
| Résolu à l'essai 2 | 4 | 3 | C21 : question de précision au lieu d'une solution (hésitation logiciel / compte), aucun ticket |
| Hors sujet | 3 | 3 | refus |
| Précision puis résolu | 2 | 2 | aucun ticket |
| Escalade refusée | 3 | 3 | aucun ticket |

## Parcours de la version minimale (vrai serveur)

| Étape | Résultat |
| --- | --- |
| 1. « My VPN keeps disconnecting every 10 minutes » | `reseau`, medium, `KB-NET-01` |
| 2. pas résolu | `KB-NET-03` |
| 3. pas résolu | brouillon : Network · 1 business day · [KB-NET-01, KB-NET-03] |
| 4. `POST /tickets` | 201 · **INC-00001** |
| 5. `GET /tickets/INC-00001` | ouvert · Network · `non_resolu_apres_essais` |

## Saisies inhabituelles (vrai modèle)

| Saisie | Réponse |
| --- | --- |
| Espaces seuls | refusée par l'API (422) ; ignorée par l'interface |
| `asdfgh`, `qsdkjqsd lkjqsd`, `123456` | « didn't understand », redemande (sans consommer la précision) |
| `hello` | message d'accueil |
| `!!!???`, `a` | question de précision |
| `printr brokn` | corrigé en « printer broken » → `materiel`, KB-HW-01 |
| `laptp wont boot` | corrigé en « laptop wont boot » → `materiel`, KB-HW-06 |
| `jfkdl vpn` | `reseau`, KB-NET-01 |
| Mots corrects (`promised`, `ransom`, `stole`, `renewing`, `choppy`) | jamais modifiés par la correction |

## Effet de la correction orthographique sur la validation

| Mesure | Sans correction | Avec correction (version sûre) |
| --- | --- | --- |
| F1 macro | 0,917 | 0,917 |
| Top-1 / Top-3 | 0,848 / 0,962 | 0,848 / 0,962 |
| Cas critiques manqués | 0 / 30 | 0 / 30 |
| Hors sujet refusés | 12 / 15 | 12 / 15 |

Aucune régression sur la validation. Le gain se voit sur les messages avec fautes de frappe.
