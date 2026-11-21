# Fiche de cadrage : classement des incidents (catégorie ou hors sujet)

> Remplir chaque rubrique en une à trois phrases. Les rubriques marquées (obligatoire) sont vérifiées par `pytest`.

## Besoin en une phrase (obligatoire)

Les techniciens de niveau 1 perdent du temps à trier chaque incident à la main : il faut ranger automatiquement le message d'un employé dans l'une des 7 catégories informatiques (réseau, matériel, logiciel, comptes et accès, sécurité, facturation, panne de service), ou le reconnaître comme hors sujet.

## Utilisateur final (obligatoire)

L'employé qui décrit son incident en anglais dans le chat. Indirectement, le technicien N1, qui reçoit des tickets déjà classés et orientés vers le bon groupe.

## Approche retenue (obligatoire)

Cocher une seule case :

- [ ] Règles métier
- [x] Machine learning
- [ ] RAG
- [ ] Modèle génératif seul

## Justification (obligatoire, citer au moins deux critères de la grille : (a) données étiquetées, (b) vérifiabilité, (c) coût par requête, (d) conséquence d'une erreur)

(a) Des données étiquetées existent en quantité : tickets Tobi-Bueck, questions Super User et Stack Exchange étiquetées par leurs tags, requêtes CLINC150 pour le hors sujet. (b) Le résultat est vérifiable : F1 macro mesuré sur des jeux écrits à la main et jamais vus à l'entraînement. (c) Le coût est faible : TF-IDF + MiniLM + LinearSVC calibré répond en quelques dizaines de millisecondes sur CPU, sans API payante.

## Données nécessaires et leur origine (obligatoire)

Entraînement : Tobi-Bueck/customer-support-tickets (Hugging Face, tickets générés, CC BY-NC 4.0), Super User et Information Security (Stack Exchange, vraies questions, CC BY-SA 4.0) et CLINC150 (vraies requêtes, CC BY 3.0) ; les titres et symptômes des 57 articles de la base servent aussi d'exemples courts. Évaluation : `data/eval/jeu_validation.csv` (120 messages) et `data/eval/jeu_independant.csv` (126 messages), écrits par le binôme et retirés de l'entraînement (anti-fuite).

## Métrique de succès et seuil d'acceptation (obligatoire)

F1 macro ≥ 0,85 sur le jeu indépendant, lu une seule fois à la fin (T12) ; mesure de départ et réglages sur le jeu de validation. Vérification : `python -m support_agent.evaluer validation`, puis `python -m support_agent.evaluer independant --final`.

## Conséquence d'une erreur et validation humaine prévue (obligatoire)

Une mauvaise catégorie donne une procédure inadaptée (temps perdu) ou envoie le ticket au mauvais groupe. Sous le seuil de confiance (`SEUIL_ABSTENTION`), l'agent s'abstient (`INDETERMINE`) : il pose une question de précision, puis propose un ticket vers le tri N1, où un technicien tranche ; un hors sujet douteux qui contient du vocabulaire informatique n'est jamais refusé, il passe aussi par un humain.

## Risques éthiques ou de confidentialité (obligatoire)

Aucune donnée personnelle à l'entraînement : tickets générés, questions publiques, requêtes anonymes ; les textes téléchargés ne sont pas redistribués (`data/raw/` et `data/processed/` hors Git), ce qui respecte les licences CC BY-NC et CC BY-SA. Les données sont surtout anglaises et en partie générées : l'agent est limité à l'anglais, et ce biais est déclaré dans le périmètre.

## Approche écartée et pourquoi (facultatif)

Règles par mots-clés : fragiles face à la variété des formulations, aux négations (« my mouse is fine, it's the Wi-Fi ») et aux fautes de frappe. Modèle génératif seul (classement « zero-shot ») : plus lent et plus coûteux, réponses non reproductibles, et catégorie parfois inventée hors de la liste.
