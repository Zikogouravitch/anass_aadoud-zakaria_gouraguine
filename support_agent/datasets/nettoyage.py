"""Nettoyage de texte commun aux trois sources."""

from __future__ import annotations

import html
import re

_BALISES = re.compile(r"<[^>]{1,40}>")  # <name>, <tel_num>, <br> ...
_FIN_SE = re.compile(r"\s*\[(closed|duplicate|on hold|migrated)\]\s*$", re.I)
_ESPACES = re.compile(r"\s+")
_MOT = re.compile(r"[a-z0-9]+")


def nettoyer(texte: str) -> str:
    """Décode le HTML, retire balises et mentions Stack Exchange, normalise les espaces."""
    texte = html.unescape(str(texte)).replace("\\n", " ").replace("\\r", " ")
    texte = _BALISES.sub(" ", texte)
    texte = _FIN_SE.sub("", texte)
    return _ESPACES.sub(" ", texte).strip()


def cle(texte: str) -> str:
    """Forme normalisée pour repérer les doublons (minuscules, mots seulement)."""
    return " ".join(_MOT.findall(texte.lower()))


def mots(texte: str) -> set[str]:
    return set(_MOT.findall(texte.lower()))


def est_anglais(texte: str) -> bool:
    """Heuristique légère : texte presque entièrement ASCII avec des mots outils anglais."""
    if not texte:
        return False
    ascii_ratio = sum(c.isascii() for c in texte) / len(texte)
    if ascii_ratio < 0.97:
        return False
    outils = {"the", "a", "is", "my", "i", "to", "not", "on", "in", "and", "of", "with", "how",
              "can", "it", "does", "for", "when", "after", "from", "why", "won't", "can't"}
    return bool(mots(texte) & outils) or len(mots(texte)) <= 4


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
