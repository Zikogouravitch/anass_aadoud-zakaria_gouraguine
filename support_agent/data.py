"""Chargement et contrôle des jeux de données versionnés."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from support_agent.config import CATEGORIES, ETIQUETTES, EVAL, PRIORITES, SAMPLE

COLONNES_TICKETS = ["text", "categorie", "priorite"]
COLONNES_KB = ["id", "categorie", "titre", "symptomes", "etapes", "escalade_si", "source"]
COLONNES_OR = ["text", "attendu", "difficulte", "erreur_connue"]


class DonneesInvalides(ValueError):
    """Le fichier ne respecte pas le format attendu."""


def _lire(chemin: Path, colonnes: list[str]) -> pd.DataFrame:
    if not chemin.exists():
        raise FileNotFoundError(chemin)
    df = pd.read_csv(chemin)
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise DonneesInvalides(f"{chemin.name} : colonnes manquantes {manquantes}")
    return df


def charger_tickets(chemin: Path = SAMPLE / "tobi_bueck_extrait.csv") -> pd.DataFrame:
    """Tickets étiquetés (texte, catégorie, priorité), sans vide ni doublon."""
    df = _lire(chemin, COLONNES_TICKETS)
    df = df.dropna(subset=["text", "categorie"]).drop_duplicates(subset=["text"])
    inconnues = set(df["categorie"]) - set(CATEGORIES)
    if inconnues:
        raise DonneesInvalides(f"catégories inconnues : {sorted(inconnues)}")
    inconnues = set(df["priorite"].dropna()) - set(PRIORITES)
    if inconnues:
        raise DonneesInvalides(f"priorités inconnues : {sorted(inconnues)}")
    return df.reset_index(drop=True)


@dataclass(frozen=True)
class Article:
    """Un article de la base de connaissances."""

    id: str
    categorie: str
    titre: str
    symptomes: str
    etapes: tuple[str, ...]
    escalade_si: str
    source: str


def charger_base(chemin: Path = SAMPLE / "base_connaissances.csv") -> list[Article]:
    """Articles de solution ; les étapes sont séparées par « | » dans le CSV."""
    df = _lire(chemin, COLONNES_KB)
    if df["id"].duplicated().any():
        raise DonneesInvalides("identifiants d'articles en double")
    return [
        Article(
            id=str(r.id),
            categorie=str(r.categorie),
            titre=str(r.titre),
            symptomes=str(r.symptomes),
            etapes=tuple(e.strip() for e in str(r.etapes).split("|") if e.strip()),
            escalade_si=str(r.escalade_si),
            source=r.source if isinstance(r.source, str) else "",  # NaN = pas de source
        )
        for r in df.itertuples(index=False)
    ]


def charger_jeu_or(chemin: Path = SAMPLE / "jeu_or.csv") -> pd.DataFrame:
    """Jeu d'or : 20 incidents courts avec la catégorie attendue."""
    return _lire(chemin, COLONNES_OR)


COLONNES_EVAL = ["text", "attendu", "articles_ok", "critique", "difficulte"]
JEUX_EVAL = ("validation", "independant")


def charger_jeu_eval(nom: str, dossier: Path = EVAL) -> pd.DataFrame:
    """Jeu d'évaluation écrit à la main : `validation` (réglage) ou `independant` (mesure finale).

    `articles_ok` liste les articles acceptés (séparés par « | »), `critique` vaut 1 si
    l'incident doit être escaladé tout de suite.
    """
    if nom not in JEUX_EVAL:
        raise ValueError(f"jeu inconnu : {nom} (attendu : {JEUX_EVAL})")
    df = _lire(dossier / f"jeu_{nom}.csv", COLONNES_EVAL)
    inconnues = set(df["attendu"]) - set(ETIQUETTES)
    if inconnues:
        raise DonneesInvalides(f"étiquettes inconnues : {sorted(inconnues)}")
    df["articles_ok"] = df["articles_ok"].fillna("")
    df["critique"] = df["critique"].astype(int)
    df["difficulte"] = df["difficulte"].fillna("")
    return df
