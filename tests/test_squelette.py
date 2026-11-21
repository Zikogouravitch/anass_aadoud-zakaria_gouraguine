"""Tests du squelette (T1) : config, données d'essai, hygiène du dépôt."""

from pathlib import Path

import pytest

from support_agent import config
from support_agent.data import (
    DonneesInvalides,
    charger_base,
    charger_jeu_or,
    charger_tickets,
)


def test_settings_par_defaut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEUIL_ABSTENTION", raising=False)
    s = config.Settings(_env_file=None)  # type: ignore[call-arg]
    assert 0 < s.seuil_abstention < 1
    assert s.ollama_active is False


def test_settings_lues_dans_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEUIL_ABSTENTION", "0.7")
    assert config.Settings(_env_file=None).seuil_abstention == 0.7  # type: ignore[call-arg]


def test_get_settings() -> None:
    assert isinstance(config.get_settings(), config.Settings)


def test_tickets_echantillon() -> None:
    df = charger_tickets()
    assert len(df) == 100
    assert set(df["categorie"]) == set(config.CATEGORIES)


def test_base_de_connaissances() -> None:
    base = charger_base()
    assert len(base) == 57
    assert {a.categorie for a in base} == set(config.CATEGORIES)
    vpn = next(a for a in base if a.id == "KB-NET-01")
    assert vpn.categorie == "reseau"
    assert len(vpn.etapes) >= 2


def test_jeu_or() -> None:
    assert len(charger_jeu_or()) == 20


def test_echantillon_leger() -> None:
    taille = sum(f.stat().st_size for f in config.SAMPLE.glob("*.csv"))
    assert taille < 10 * 1024 * 1024


def test_colonnes_manquantes(tmp_path: Path) -> None:
    faux = tmp_path / "faux.csv"
    faux.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(DonneesInvalides):
        charger_tickets(faux)


def test_categorie_inconnue(tmp_path: Path) -> None:
    faux = tmp_path / "faux.csv"
    faux.write_text("text,categorie,priorite\nhello,cuisine,low\n", encoding="utf-8")
    with pytest.raises(DonneesInvalides):
        charger_tickets(faux)


def test_priorite_inconnue(tmp_path: Path) -> None:
    faux = tmp_path / "faux.csv"
    faux.write_text("text,categorie,priorite\nhello,reseau,urgent\n", encoding="utf-8")
    with pytest.raises(DonneesInvalides):
        charger_tickets(faux)


def test_article_en_double(tmp_path: Path) -> None:
    faux = tmp_path / "kb.csv"
    ligne = "KB-1,reseau,t,s,a|b,e,\n"
    faux.write_text(
        "id,categorie,titre,symptomes,etapes,escalade_si,source\n" + ligne + ligne,
        encoding="utf-8",
    )
    with pytest.raises(DonneesInvalides):
        charger_base(faux)


def test_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        charger_base(tmp_path / "absent.csv")


def test_aucun_secret_versionne() -> None:
    ignores = (config.RACINE / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignores
    exemple = (config.RACINE / ".env.example").read_text(encoding="utf-8")
    assert "API_KEY=\n" in exemple  # le modèle ne contient aucune vraie clé
