# Données du projet

Règle du cours respectée : uniquement des données publiques, générées ou anonymisées. Rien n'est envoyé à un tiers.

## Sources

| Source | Nature | Licence | Usage |
| --- | --- | --- | --- |
| [Tobi-Bueck/customer-support-tickets](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | Tickets **générés**, longs (≈ 60 mots) | CC BY-NC 4.0 | 7 catégories ; seule source pour `facturation` et `panne_service` |
| [Super User](https://superuser.com), dump [marianna13/superuser](https://huggingface.co/datasets/marianna13/superuser) | **Vraies** questions d'utilisateurs, courtes (≈ 10 mots) | CC BY-SA 4.0 (Stack Exchange) | `reseau`, `materiel`, `logiciel`, `compte_acces`, `securite` |
| [API Stack Exchange](https://api.stackexchange.com) (Super User, Information Security) | **Vraies** questions, courtes | CC BY-SA 4.0 | renforce `securite` et `compte_acces` (sans clé, réponses mises en cache) |
| [CLINC150](https://huggingface.co/datasets/clinc/clinc_oos) (Larson et al., 2019) | **Vraies** requêtes (crowdsourcing) | CC BY 3.0 | classe `hors_sujet` (météo, cuisine, voyages…) |
| `data/sample/base_connaissances.csv` | 57 articles rédigés par le binôme | — | réponses citées |
| `data/eval/` | 246 incidents écrits à la main | — | réglage (120) et mesure finale (126) |

Les textes téléchargés ne sont pas redistribués : `data/raw/` et `data/processed/` sont ignorés par Git et sont reconstruits par le script.

## Étiquetage

- **Tobi-Bueck** : anglais, type `Incident` ou `Problem`. Un tag de sécurité donne `securite`. Sinon, la file `Billing and Payments` donne `facturation` et la file `Service Outages and Maintenance` donne `panne_service`. Sinon, c'est le premier tag reconnu qui décide (Network → `reseau`, Hardware → `materiel`…). Les files commerciales et RH sont exclues.
- **Super User / Stack Exchange** : la catégorie vient des tags (`vpn`, `printer`, `password`, `malware`…). Les tags de sécurité et de compte l'emportent. Un titre qui touche deux autres catégories est écarté, car ambigu. On garde seulement les titres en anglais, de 3 à 40 mots, qui décrivent un incident (« not working », « can't », « keeps disconnecting »…). Un mot comme « virus » ne suffit que si la phrase raconte un vécu (« my », « I »…).
- **CLINC150** : intentions hors informatique, environ 10 exemples par intention. Sont exclus : tout le domaine banque et carte de crédit (trop proche de la facturation : « refund » et « credit card expired » partaient en hors sujet sur la validation), les intentions proches des comptes ou du matériel (appareil perdu, réglages), et les formules de politesse.

## Construction

```powershell
python -m support_agent.datasets.construire   # ≈ 1 min la 1re fois (téléchargements), puis cache
python -m support_agent.decrire               # recalcule les chiffres de la fiche
```

Étapes de la construction :
- nettoyage (HTML, balises, espaces) ;
- coupure des textes à 150 mots ;
- retrait des doublons (un texte présent avec deux catégories est écarté) ;
- plafond de 1 200 tickets Tobi-Bueck par catégorie ;
- **retrait anti-fuite** de tout texte identique ou proche (Jaccard ≥ 0,6) d'un texte d'évaluation.

## Jeux d'évaluation

| Jeu | Lignes | Composition | Rôle |
| --- | --- | --- | --- |
| `jeu_validation.csv` | 120 | 15 × 7 catégories + 15 hors sujet ; 30 critiques | réglage (seuils, paramètres) |
| `jeu_independant.csv` | 126 | 16 × 7 catégories + 14 hors sujet ; 32 critiques | mesure finale, **lue une seule fois** (T12) |

Colonnes :
- `text` : le message de l'employé ;
- `attendu` : l'étiquette attendue ;
- `articles_ok` : les articles acceptés, séparés par `|` ;
- `critique` : 1 pour la sécurité ou une panne générale (escalade immédiate) ;
- `difficulte` : texte vague, texte court, vocabulaire partagé, négation, incident mêlé ou faute de frappe.

Les deux jeux n'ont aucune phrase en commun et ne reprennent pas la formulation des articles.
