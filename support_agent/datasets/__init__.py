"""Construction du jeu d'entraînement à partir de trois sources publiques.

- Tobi-Bueck (Hugging Face, CC BY-NC 4.0) : tickets générés, longs, 7 catégories.
- Super User / Stack Exchange (CC BY-SA 4.0) : vraies questions d'utilisateurs, courtes.
- CLINC150 (CC BY 3.0) : vraies requêtes hors informatique -> classe `hors_sujet`.

Point d'entrée : ``python -m support_agent.datasets.construire``.
"""
