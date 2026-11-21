# Résultats — Partie 04 (T5 : endpoint `/chat`)

## Tests et qualité du code

| Outil | Résultat |
| --- | --- |
| `pytest` | **117 passed**, dont 37 dans `tests/test_chat.py` |
| Couverture | **99 %** (1 103 instructions) |
| `ruff` | All checks passed |
| `mypy` | Success: no issues found in 34 source files |

Critère de T5 : `test_incident_resolu_ne_cree_aucun_ticket` passe. Dans ce cas, la réponse ne contient aucun brouillon, aucun fichier de tickets n'est créé, et le journal ne contient que `solution_proposee → resolue`.

## Essai réel (serveur uvicorn + vrai modèle)

| Scénario | Tours | Résultat |
| --- | --- | --- |
| VPN (scénario de la fiche) | message → pas résolu → pas résolu | `KB-NET-01` (essai 1) → `KB-NET-03` (essai 2) → escalade proposée, brouillon `reseau`, motif `non_resolu_apres_essais` |
| Outlook | message → « It works now, thanks! » | `KB-SW-02` → `resolue`, aucun ticket |
| Message vague | « It does not work » → « the printer on the second floor shows offline » | question de précision → `KB-HW-01` |
| Phishing | 1 message | escalade immédiate, `securite`, priorité high, `KB-SEC-01` |
| Serveur en panne | 1 message | escalade immédiate, `panne_service`, priorité high |
| Pizza | 1 message | `hors_sujet`, refus poli |

## Temps de réponse

| Mesure | Sans préchargement | Avec préchargement |
| --- | --- | --- |
| API prête après le démarrage | — | ~33 s |
| 1er message | 40,6 s | 2,1 s |
| Messages suivants | 0,01 – 0,08 s | 0,01 – 0,08 s |
