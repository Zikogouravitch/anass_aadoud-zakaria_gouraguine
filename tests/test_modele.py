"""Tests du modèle (T3) : base de connaissances, priorité, classement, sauvegarde, CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from support_agent import encodeur as module_encodeur
from support_agent import predict, train
from support_agent.config import HORS_SUJET, INDETERMINE
from support_agent.kb import BaseConnaissances
from support_agent.modele import (
    Hyper,
    ModeleSupport,
    Prediction,
    exemples_base,
    trop_vague,
    vocabulaire_base,
)
from support_agent.priorite import est_critique, priorite, touche_beaucoup
from tests.conftest import FauxEncodeur

# --- règles simples --------------------------------------------------------------


@pytest.mark.parametrize(("texte", "vague"), [
    ("It does not work", True), ("Help!! something is wrong", True),
    ("vpn not connecting", False), ("Locked out", False),
])
def test_trop_vague(texte: str, vague: bool) -> None:
    assert trop_vague(texte) is vague


def test_vocabulaire_base(modele: ModeleSupport) -> None:
    vocab = vocabulaire_base(modele.kb.articles)
    assert {"refund", "printer", "phishing"} <= vocab
    assert "the" not in vocab


@pytest.mark.parametrize(("texte", "categorie", "attendu"), [
    ("Antivirus alert on my PC", "securite", "high"),
    ("The whole team cannot print", "materiel", "high"),
    ("Outlook is down since this morning", "logiciel", "high"),
    ("Can you add a user to our plan?", "facturation", "low"),
    ("Please give me access to the HR folder", "compte_acces", "low"),
    ("Excel freezes on my big file", "logiciel", "medium"),
])
def test_priorite(texte: str, categorie: str, attendu: str) -> None:
    assert priorite(texte, categorie) == attendu


def test_critique() -> None:
    assert est_critique("My laptop is slow", "panne_service")
    assert est_critique("No one can log in", "compte_acces")
    assert touche_beaucoup("Customers cannot pay")
    assert not est_critique("My mouse does not move", "materiel")


# --- base de connaissances -------------------------------------------------------


def test_kb_recherche(encodeur: FauxEncodeur) -> None:
    kb = BaseConnaissances(encodeur)
    res = kb.chercher("VPN disconnects or does not connect")
    assert res[0].article.id == "KB-NET-01"
    assert len(res) == 3 and res[0].score >= res[1].score
    assert all(r.article.categorie == "materiel"
               for r in kb.chercher("VPN disconnects", categorie="materiel"))
    favori = kb.chercher("VPN disconnects", bonus={"materiel": 5.0})[0]
    assert favori.article.categorie == "materiel"
    assert kb.par_id("KB-NET-01") is not None and kb.par_id("KB-XXX") is None


def test_exemples_base(modele: ModeleSupport) -> None:
    ex = exemples_base(modele.kb.articles)
    assert len(ex) > 57 and set(ex["source"]) == {"base"}


# --- classement ------------------------------------------------------------------


def test_prediction_incident(modele: ModeleSupport) -> None:
    p = modele.predire("My VPN keeps disconnecting")
    assert p.categorie == "reseau"
    assert p.articles[0]["id"] == "KB-NET-01"
    assert p.articles[0]["etapes"]
    assert p.en_dict()["categorie"] == "reseau"


def test_prediction_hors_sujet(modele: ModeleSupport, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modele, "probabilites",
                        lambda t, v=None: pd.DataFrame([{"hors_sujet": 0.95, "reseau": 0.05}]))
    p = modele.predire("What is the weather in Rome")
    assert p.categorie == HORS_SUJET and p.articles == [] and not p.critique
    assert p.priorite == "low"


def test_prediction_vague(modele: ModeleSupport) -> None:
    p = modele.predire("It does not work")
    assert p.categorie == INDETERMINE and p.articles == []


def test_hors_sujet_douteux_avec_vocabulaire_it(modele: ModeleSupport,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    def proba(textes: list[str], vecteurs: Any = None) -> pd.DataFrame:
        return pd.DataFrame([{"hors_sujet": 0.7, "facturation": 0.3}])

    monkeypatch.setattr(modele, "probabilites", proba)
    p = modele.predire("Where is my refund")
    assert p.categorie == INDETERMINE
    assert p.categorie_probable == "facturation"
    assert p.articles


def test_seuil_abstention(modele: ModeleSupport, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modele, "probabilites",
                        lambda t, v=None: pd.DataFrame([{"reseau": 0.4, "materiel": 0.35,
                                                         "logiciel": 0.25}]))
    modele.hyper = Hyper(seuil=0.5)
    try:
        p = modele.predire("Strange printer and wifi behaviour")
    finally:
        modele.hyper = Hyper(C=1.0, seuil=0.3, min_df=1)
    assert p.categorie == INDETERMINE and p.categorie_probable == "reseau"
    assert len(p.alternatives) == 3


def test_non_entraine() -> None:
    with pytest.raises(RuntimeError):
        ModeleSupport().utiliser(FauxEncodeur()).probabilites(["x"])


def test_sauver_charger(modele: ModeleSupport, tmp_path: Path, encodeur: FauxEncodeur) -> None:
    chemin = modele.sauver(tmp_path / "m.joblib")
    relu = ModeleSupport.charger(chemin)
    assert relu._encodeur is None  # l'encodeur n'est pas sauvegardé
    relu.utiliser(encodeur, modele.kb)
    assert relu.predire("My VPN keeps disconnecting").categorie == "reseau"


def test_charger_erreurs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ModeleSupport.charger(tmp_path / "absent.joblib")
    import joblib

    joblib.dump({"pas": "un modèle"}, tmp_path / "x.joblib")
    with pytest.raises(TypeError):
        ModeleSupport.charger(tmp_path / "x.joblib")


def test_proprietes_paresseuses(monkeypatch: pytest.MonkeyPatch, encodeur: FauxEncodeur) -> None:
    monkeypatch.setattr("support_agent.modele.charger_encodeur", lambda nom: encodeur)
    m = ModeleSupport()
    assert m.encodeur is encodeur
    assert len(m.kb.articles) == 57


# --- entraînement ----------------------------------------------------------------


def test_entrainer(petit_jeu: pd.DataFrame, encodeur: FauxEncodeur, tmp_path: Path,
                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ModeleSupport, "kb", property(lambda s: BaseConnaissances(encodeur)))
    jeu = pd.concat([petit_jeu] * 3, ignore_index=True)  # assez de lignes pour 80/20
    jeu["text"] = jeu["text"] + pd.Series(range(len(jeu))).astype(str).radd(" n")
    m = train.entrainer(jeu, encodeur=encodeur, hyper=Hyper(min_df=1),
                        chemin=tmp_path / "support.joblib", cache=tmp_path)
    assert 0 <= m["test_20pct"]["f1_macro"] <= 1
    assert "exactitude_par_source" in m["test_20pct"]
    assert (tmp_path / "support.joblib").exists()
    assert json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))["lignes"] == 36
    rapide = train.entrainer(jeu, encodeur=encodeur, rapide=True, hyper=Hyper(min_df=1),
                             chemin=tmp_path / "support.joblib", cache=tmp_path)
    assert "test_20pct" not in rapide


def test_vecteurs_en_cache(tmp_path: Path) -> None:
    class Compteur(FauxEncodeur):
        appels = 0

        def encode(self, textes: list[str]) -> np.ndarray:
            Compteur.appels += 1
            return super().encode(textes)

    enc = Compteur()
    a = train.vecteurs_en_cache(["vpn down", "printer"], enc, tmp_path)
    b = train.vecteurs_en_cache(["vpn down", "printer"], enc, tmp_path)
    assert np.allclose(a, b) and Compteur.appels == 1


def test_train_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                    capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        train.main(["--donnees", str(tmp_path / "absent.csv")])
    f = tmp_path / "e.csv"
    pd.DataFrame({"text": ["a"], "categorie": ["reseau"], "source": ["s"]}).to_csv(f)
    faux = {"lignes": 1, "duree_s": 0.1, "test_20pct": {
        "f1_macro": 0.9, "exactitude": 0.9, "exactitude_par_source": {}, "abstention": 0.0}}
    monkeypatch.setattr(train, "entrainer", lambda df, rapide: faux)
    train.main(["--donnees", str(f)])
    assert '"f1_macro_test": 0.9' in capsys.readouterr().out


# --- ligne de commande -----------------------------------------------------------


def _pred(**kw: Any) -> Prediction:
    base: dict[str, Any] = dict(texte="t", categorie="reseau", categorie_probable="reseau",
                                confiance=0.9, priorite="high", critique=True,
                                articles=[{"id": "KB-NET-01", "titre": "VPN", "score": 0.9,
                                           "etapes": ["Restart"], "escalade_si": "always"},
                                          {"id": "KB-NET-02", "titre": "Wi-Fi", "score": 0.5,
                                           "etapes": [], "escalade_si": ""}])
    base.update(kw)
    return Prediction(**base)


def test_afficher() -> None:
    texte = predict.afficher(_pred())
    assert "KB-NET-01" in texte and "CAS CRITIQUE" in texte and "1. Restart" in texte
    assert "INDETERMINE" in predict.afficher(_pred(categorie=INDETERMINE, critique=False))
    assert "hors sujet" in predict.afficher(_pred(categorie=HORS_SUJET, articles=[]))


def test_predict_main(monkeypatch: pytest.MonkeyPatch, modele: ModeleSupport,
                      capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(lambda: modele))
    predict.main(["My", "VPN", "keeps", "disconnecting"])
    assert "KB-NET-01" in capsys.readouterr().out
    predict.main(["--json", "My VPN keeps disconnecting"])
    assert json.loads(capsys.readouterr().out)["categorie"] == "reseau"


def test_minilm_enveloppe(monkeypatch: pytest.MonkeyPatch) -> None:
    class FauxST:
        def __init__(self, nom: str, device: str) -> None:
            self.nom, self.max_seq_length = nom, 512

        def encode(self, textes: list[str], **kw: Any) -> list[list[float]]:
            return [[1.0, 0.0] for _ in textes]

    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FauxST)
    module_encodeur.charger_encodeur.cache_clear()
    enc = module_encodeur.charger_encodeur("faux")
    assert enc.encode(["a", "b"]).shape == (2, 2)
    module_encodeur.charger_encodeur.cache_clear()
