# Fiche de cadrage : escalade et ticket pré-rempli

> Remplir chaque rubrique en une à trois phrases. Les rubriques marquées (obligatoire) sont vérifiées par `pytest`.

## Besoin en une phrase (obligatoire)

Les cas critiques (sécurité, panne générale) sont retardés au milieu des demandes simples : l'agent doit envoyer tout de suite au bon groupe de techniciens les incidents critiques et ceux qu'il ne résout pas, avec un ticket déjà rempli, sans créer de ticket inutile.

## Utilisateur final (obligatoire)

L'employé, qui confirme la création du ticket puis le suit par son identifiant (`INC-00001`). Le technicien, qui reçoit le ticket dans son groupe, cas critiques en tête, et met à jour son statut.

## Approche retenue (obligatoire)

Cocher une seule case :

- [x] Règles métier
- [ ] Machine learning
- [ ] RAG
- [ ] Modèle génératif seul

## Justification (obligatoire, citer au moins deux critères de la grille : (a) données étiquetées, (b) vérifiabilité, (c) coût par requête, (d) conséquence d'une erreur)

(d) Conséquence d'une erreur : rater un cas critique est le risque le plus grave du projet, donc la décision doit être lisible, prévisible et auditable plutôt qu'apprise. (b) Vérifiabilité : chaque règle (R1 cas critique, R2 article « always », R3 deux échecs, R4 demande de l'employé, R5 catégorie indéterminée) est testée une à une. (a) Il n'existe pas de données étiquetées d'escalade réelles pour apprendre ces décisions.

## Données nécessaires et leur origine (obligatoire)

Aucune donnée d'entraînement : les règles utilisent la catégorie et la priorité du modèle, le champ `escalade_si` des articles, l'historique de la conversation (nombre d'essais) et une table catégorie → groupe → délai. Pour l'évaluation, `data/eval/conversations.json` contient 30 conversations écrites par le binôme, dont 10 doivent finir en ticket.

## Métrique de succès et seuil d'acceptation (obligatoire)

Au plus 1 cas critique manqué sur les 32 du jeu indépendant ; les 30 conversations donnent 10 tickets, tous attendus (bonne catégorie, bon motif), et aucun ticket en trop ; au moins 90 % des hors sujet refusés. Vérification : `python -m support_agent.bilan_tickets`, `python -m support_agent.evaluer` et `tests/test_escalade.py`.

## Conséquence d'une erreur et validation humaine prévue (obligatoire)

Un cas critique non escaladé expose à un risque de sécurité (compte compromis, rançongiciel) ; un ticket créé à tort ajoute de la charge aux techniciens. Le ticket n'est créé qu'après confirmation explicite de l'employé (un simple « yes » ne suffit pas) ; il est ensuite traité par un technicien, qui peut changer son statut et ajouter une note ; en cas de doute, il part au tri N1.

## Risques éthiques ou de confidentialité (obligatoire)

Les tickets contiennent la description écrite par l'employé : ils sont stockés localement en JSON Lines (`tickets/`, hors Git) et ne sont envoyés à aucun tiers. L'application n'a pas d'authentification (hors périmètre) : l'agent ne demande jamais de mot de passe, et la clé `API_KEY` protège l'API.

## Approche écartée et pourquoi (facultatif)

Machine learning pour décider de l'escalade : pas de données réelles pour l'entraîner, et une décision opaque sur le point le plus sensible. Escalade systématique de chaque incident : simple et sûre, mais elle recrée la surcharge des techniciens N1 que le projet veut réduire.
