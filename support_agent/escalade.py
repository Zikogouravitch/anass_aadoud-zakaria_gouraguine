"""Règles d'escalade : quand passer la main à un technicien, vers quel groupe, avec quel délai.

Chaque règle est une petite fonction pure, testée une à une (tests/test_escalade.py).

R1 cas critique : sécurité, panne de service ou beaucoup de personnes touchées
   -> `cas_critique`, escalade dès le 1er message
R2 article « always » : l'article dit qu'un technicien est toujours nécessaire
   -> `article_exige_technicien`, escalade dès le 1er message
R3 échecs : 2 solutions essayées sans succès, ou plus aucun article
   -> `non_resolu_apres_essais`
R4 demande : l'employé demande un technicien -> `demande_utilisateur`
R5 indéterminé : catégorie incertaine après la question de précision
   -> `categorie_indeterminee`, ticket vers le tri N1
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from support_agent.config import HORS_SUJET, INDETERMINE

MAX_TENTATIVES = 2


class Motif(StrEnum):
    CRITIQUE = "cas_critique"
    ARTICLE = "article_exige_technicien"
    ECHECS = "non_resolu_apres_essais"
    DEMANDE = "demande_utilisateur"
    INDETERMINE = "categorie_indeterminee"


GROUPES = {
    "securite": "Security team",
    "panne_service": "Operations",
    "compte_acces": "Identity & access",
    "facturation": "Billing",
    "reseau": "Network",
    "materiel": "Hardware & workplace",
    "logiciel": "Applications",
    INDETERMINE: "Service desk N1 (triage)",
}
# Délai de prise en charge annoncé à l'employé, selon la priorité
SLA = {"high": "4 hours", "medium": "1 business day", "low": "3 business days"}

_TOUJOURS = re.compile(r"^\s*always\b", re.I)


def exige_technicien(article: dict[str, Any] | None) -> bool:
    """R2 : l'article indique qu'un technicien est toujours nécessaire (« always: ... »)."""
    if not article:
        return False
    return bool(_TOUJOURS.match(str(article.get("escalade_si", ""))))


def motif_immediat(categorie: str, critique: bool,
                   article: dict[str, Any] | None) -> Motif | None:
    """R1 puis R2 : escalade dès le premier message, avant tout essai."""
    if categorie in (INDETERMINE, HORS_SUJET):
        return None
    if critique:
        return Motif.CRITIQUE
    if exige_technicien(article):
        return Motif.ARTICLE
    return None


def apres_echec(tentatives: int, reste_un_article: bool) -> bool:
    """R3 : vrai s'il faut escalader au lieu de proposer une autre solution."""
    return tentatives >= MAX_TENTATIVES or not reste_un_article


def groupe(categorie: str | None) -> str:
    """Groupe de techniciens qui reçoit le ticket ; tri N1 si la catégorie est inconnue."""
    return GROUPES.get(categorie or INDETERMINE, GROUPES[INDETERMINE])


def priorite_ticket(priorite: str | None, critique: bool, motif: Motif | None) -> str:
    """Un cas critique est toujours `high` ; sinon la priorité calculée par le modèle."""
    if critique or motif == Motif.CRITIQUE:
        return "high"
    return priorite if priorite in SLA else "medium"


def delai(priorite: str) -> str:
    return SLA.get(priorite, SLA["medium"])
