"""Tests de la construction des données (T2) : sans réseau, sur de petits tableaux."""

from pathlib import Path

import pandas as pd
import pytest

from support_agent import config
from support_agent.data import DonneesInvalides, charger_jeu_eval
from support_agent.datasets import clinc, construire, superuser, tobi_bueck
from support_agent.datasets.nettoyage import cle, est_anglais, jaccard, mots, nettoyer

# --- nettoyage -------------------------------------------------------------------


def test_nettoyer() -> None:
    assert nettoyer("VPN &amp; Wi-Fi <name>  down [closed]") == "VPN & Wi-Fi down"
    assert nettoyer("Hello,\\n\\nmy printer") == "Hello, my printer"


def test_cle_et_jaccard() -> None:
    assert cle("Wi-Fi DOWN!!") == cle("wi fi down")
    assert jaccard(mots("vpn is down"), mots("the vpn is down")) == 0.75
    assert jaccard(set(), {"a"}) == 0.0


def test_est_anglais() -> None:
    assert est_anglais("My VPN is not working")
    assert est_anglais("Outlook crash")
    assert not est_anglais("Impressora não está funcionando")
    assert not est_anglais("")


# --- Tobi-Bueck ------------------------------------------------------------------


def _tobi(**kw: object) -> dict[str, object]:
    ligne: dict[str, object] = {
        "subject": "VPN down", "body": "It drops.", "type": "Incident", "language": "en",
        "queue": "IT Support", "priority": "high", "tag_1": "Network", "tag_2": None,
    }
    ligne.update(kw)
    return ligne


def test_tobi_categories() -> None:
    brut = pd.DataFrame([
        _tobi(),
        _tobi(queue="Billing and Payments", tag_1="Feedback"),
        _tobi(queue="Billing and Payments", tag_1="Security"),  # la sécurité l'emporte
        _tobi(queue="Service Outages and Maintenance", tag_1="IT"),
        _tobi(queue="Sales and Pre-Sales"),  # file exclue
        _tobi(language="de"),  # autre langue
        _tobi(type="Request"),  # pas un incident
        _tobi(tag_1="Marketing"),  # aucun tag reconnu
    ])
    df = tobi_bueck.preparer(brut)
    assert df["categorie"].tolist() == ["reseau", "facturation", "securite", "panne_service"]
    assert df["text"].iloc[0] == "VPN down. It drops"
    assert set(df["source"]) == {"tobi_bueck"}


# --- Super User ------------------------------------------------------------------


def test_superuser_categorie() -> None:
    assert superuser.categorie(["vpn", "windows-10"]) == "reseau"
    assert superuser.categorie(["printer", "malware"]) == "securite"  # prioritaire
    assert superuser.categorie(["wifi", "laptop"]) is None  # ambigu
    assert superuser.categorie(["linux"]) is None


def test_superuser_filtre_incidents() -> None:
    assert superuser.decrit_incident("My VPN keeps disconnecting")
    assert superuser.decrit_incident("I think my PC has a virus")
    assert not superuser.decrit_incident("Can a virus melt the CPU?")
    assert not superuser.decrit_incident("Best VPN for gaming")


def test_superuser_preparer() -> None:
    titres = pd.Series(["Wi-Fi keeps dropping on my laptop", "Best router 2014",
                        "Impressora não funciona", "Printer not printing"])
    tags = pd.Series([["wireless-networking"], ["router"], ["printer"], ["printer"]])
    df = superuser.preparer(titres, tags, "superuser")
    assert df["text"].tolist() == ["Wi-Fi keeps dropping on my laptop", "Printer not printing"]
    assert df["categorie"].tolist() == ["reseau", "materiel"]


# --- CLINC150 --------------------------------------------------------------------


def test_clinc_exclut_intentions_proches() -> None:
    noms = ["weather", "card_declined", "greeting", "recipe"]
    brut = pd.DataFrame({"text": ["is it sunny", "my card was declined", "hi", "pasta recipe"],
                         "intent": [0, 1, 2, 3]})
    df = clinc.preparer(brut, noms, n=10)
    assert sorted(df["text"]) == ["Is it sunny", "Pasta recipe"]
    assert set(df["categorie"]) == {config.HORS_SUJET}


# --- construction ----------------------------------------------------------------


def test_dedoublonner_retire_conflits() -> None:
    df = pd.DataFrame({
        "text": ["VPN down", "vpn  DOWN", "Printer jam", "Printer jam!", "!!!"],
        "categorie": ["reseau", "reseau", "materiel", "logiciel", "reseau"],
    })
    assert construire.dedoublonner(df)["text"].tolist() == ["VPN down"]


def test_plafonner() -> None:
    df = pd.DataFrame({"text": list("abcdefg"), "categorie": ["x"] * 5 + ["y"] * 2,
                       "source": ["s"] * 6 + ["autre"]})
    res = construire.plafonner(df, "s", 2)
    assert (res[res.source == "s"].groupby("categorie").size() <= 2).all()
    assert (res.source == "autre").sum() == 1


def test_retirer_fuites() -> None:
    df = pd.DataFrame({"text": ["My VPN keeps disconnecting every 10 minutes",
                                "my vpn keeps disconnecting every ten minutes at home",
                                "Printer is offline"]})
    propre, n = construire.retirer_fuites(df, ["My VPN keeps disconnecting every 10 minutes"])
    assert n == 2
    assert propre["text"].tolist() == ["Printer is offline"]


def test_couper() -> None:
    assert construire.couper("a b c", 2) == "a b"
    assert construire.couper("a b", 5) == "a b"


def test_construire_bout_en_bout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def faux(cat: str, src: str, textes: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"text": textes, "categorie": cat, "priorite": None, "source": src})

    monkeypatch.setattr(tobi_bueck, "charger", lambda: faux("facturation", "tobi_bueck",
                                                            ["Charged twice", "Wrong invoice"]))
    monkeypatch.setattr(superuser, "charger", lambda: faux("reseau", "superuser",
                                                           ["VPN drops", "Wi-Fi slow"]))
    monkeypatch.setattr(clinc, "charger", lambda n: faux("hors_sujet", "clinc150", ["Weather?"]))
    monkeypatch.setattr(construire, "PROCESSED", tmp_path)
    monkeypatch.setattr(construire, "textes_evaluation", lambda: ["VPN drops"])
    resume = construire.construire()
    assert resume["lignes_finales"] == 4
    assert resume["retires_anti_fuite"] == 1
    assert (tmp_path / "entrainement.csv").exists()
    assert (tmp_path / "resume.json").exists()


# --- jeux d'évaluation -----------------------------------------------------------


@pytest.mark.parametrize(("nom", "lignes", "critiques"), [("validation", 120, 30),
                                                           ("independant", 126, 32)])
def test_jeux_evaluation(nom: str, lignes: int, critiques: int) -> None:
    df = charger_jeu_eval(nom)
    assert len(df) == lignes
    assert df["critique"].sum() == critiques
    assert set(df["attendu"]) == set(config.ETIQUETTES)
    assert df["text"].is_unique
    articles = set(pd.read_csv(config.SAMPLE / "base_connaissances.csv")["id"])
    for liste, attendu in zip(df["articles_ok"], df["attendu"], strict=True):
        if attendu == config.HORS_SUJET:
            assert liste == ""
        else:
            assert liste and set(liste.split("|")) <= articles, liste


def test_jeux_sans_recouvrement() -> None:
    v = set(charger_jeu_eval("validation")["text"].map(cle))
    i = set(charger_jeu_eval("independant")["text"].map(cle))
    assert not v & i


def test_jeu_eval_inconnu() -> None:
    with pytest.raises(ValueError):
        charger_jeu_eval("test")


def test_jeu_eval_etiquette_inconnue(tmp_path: Path) -> None:
    (tmp_path / "jeu_validation.csv").write_text(
        "text,attendu,articles_ok,critique,difficulte\nhi,cuisine,,0,\n", encoding="utf-8")
    with pytest.raises(DonneesInvalides):
        charger_jeu_eval("validation", tmp_path)
