"""Fiches de cadrage (docs/cadrage/cas*-*.md) : les rubriques obligatoires sont remplies."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from support_agent.config import RACINE

DOSSIER = RACINE / "docs" / "cadrage"
FICHES = sorted(DOSSIER.glob("cas*-*.md"))
OBLIGATOIRES = [
    "Besoin en une phrase",
    "Utilisateur final",
    "Approche retenue",
    "Justification",
    "Données nécessaires et leur origine",
    "Métrique de succès et seuil d'acceptation",
    "Conséquence d'une erreur et validation humaine prévue",
    "Risques éthiques ou de confidentialité",
]
APPROCHES = ["Règles métier", "Machine learning", "RAG", "Modèle génératif seul"]


def rubriques(texte: str) -> dict[str, str]:
    """Titre de rubrique (sans « (obligatoire…) ») -> contenu."""
    parties = re.split(r"^## (.+)$", texte, flags=re.M)
    return {re.sub(r"\s*\(.*$", "", titre).strip(): corps.strip()
            for titre, corps in zip(parties[1::2], parties[2::2], strict=True)}


def test_au_moins_une_fiche() -> None:
    assert FICHES, f"aucune fiche cas*-*.md dans {DOSSIER}"
    assert (DOSSIER / "TEMPLATE.md").exists()


@pytest.mark.parametrize("fiche", FICHES, ids=lambda p: p.name)
def test_fiche_complete(fiche: Path) -> None:
    texte = fiche.read_text(encoding="utf-8")
    titre = texte.splitlines()[0]
    assert titre.startswith("# Fiche de cadrage : ") and "<nom du cas>" not in titre
    r = rubriques(texte)
    for nom in OBLIGATOIRES:
        assert r.get(nom), f"{fiche.name} : rubrique « {nom} » vide ou absente"

    cochees = re.findall(r"^- \[[xX]\] (.+)$", r["Approche retenue"], flags=re.M)
    assert len(cochees) == 1, f"{fiche.name} : cocher une seule approche ({cochees})"
    assert cochees[0].strip() in APPROCHES

    criteres = set(re.findall(r"\(([abcd])\)", r["Justification"]))
    assert len(criteres) >= 2, f"{fiche.name} : citer au moins deux critères (a)-(d)"


def test_rubriques_detecte_une_fiche_vide(tmp_path: Path) -> None:
    modele = (DOSSIER / "TEMPLATE.md").read_text(encoding="utf-8")
    r = rubriques(modele)
    assert set(OBLIGATOIRES) <= set(r)
    assert not r["Besoin en une phrase"]  # le modèle vierge ne passerait pas
    assert not re.findall(r"^- \[[xX]\]", r["Approche retenue"], flags=re.M)
