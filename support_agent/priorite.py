"""Priorité par règles lisibles.

Les priorités de Tobi-Bueck sont peu cohérentes (50 % de priorité exacte en apprenant
dessus) : des règles explicites sont plus fiables et faciles à justifier.
"""

from __future__ import annotations

import re

CRITIQUES = {"securite", "panne_service"}

_ETENDUE = re.compile(
    r"\b(?:everyone|everybody|nobody|no one|whole|entire|all (?:users|staff|customers|of us"
    r"|employees|agents|visitors)|every (?:user|agent|branch|customer)|company[- ]wide"
    r"|the team|our team|department|customers?)\b",
    re.I,
)
_URGENCE = re.compile(
    r"\b(?:urgent|asap|immediately|blocked|production|deadline|can'?t work|cannot work"
    r"|down|outage|stolen|ransom|encrypted|hacked)\b",
    re.I,
)
_DEMANDE = re.compile(
    r"^(?:please|can you|could you|how do i|how can i|i need|i want|i would like|when will)"
    r"|\?\s*$",
    re.I,
)


def touche_beaucoup(texte: str) -> bool:
    """Le message décrit un problème qui touche plusieurs personnes ou les clients."""
    return bool(_ETENDUE.search(texte))


def est_critique(texte: str, categorie: str) -> bool:
    """Sécurité, panne de service, ou tout incident qui touche beaucoup de monde."""
    return categorie in CRITIQUES or touche_beaucoup(texte)


def priorite(texte: str, categorie: str) -> str:
    """high, medium ou low à partir de la catégorie et du message."""
    if categorie in CRITIQUES or _ETENDUE.search(texte) or _URGENCE.search(texte):
        return "high"
    if _DEMANDE.search(texte.strip()) and categorie in {"facturation", "compte_acces"}:
        return "low"
    return "medium"
