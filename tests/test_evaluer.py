"""Tests de la mesure (T7) : calculs, JSON écrit, protection du jeu indépendant."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from support_agent import evaluer
from support_agent.modele import ModeleSupport
from tests.test_chat import Bouchon

LIGNES = [
    # text, attendu, articles_ok, critique, difficulte
    ("My VPN keeps disconnecting", "reseau", "KB-NET-01", 0, ""),           # top-1 et top-3
    ("VPN and intranet", "reseau", "KB-NET-03", 0, "vocabulaire partagé"),  # top-3 seulement
    ("The printer is jammed", "materiel", "KB-HW-01", 0, ""),               # top-1 et top-3
    ("vpn on my printer", "materiel", "KB-HW-01", 0, "incident mêlé"),       # mal classé
    ("I clicked a phishing link", "securite", "KB-SEC-01", 1, ""),          # top-1 et top-3
    ("The printer leaks after phishing", "securite", "KB-SEC-02", 1, ""),     # critique manqué
    ("What's the weather?", "hors_sujet", "", 0, ""),
    ("It does not work", "hors_sujet", "", 0, "texte court"),                # non refusé
]


@pytest.fixture
def dossier(tmp_path: Path) -> Path:
    d = tmp_path / "eval"
    d.mkdir()
    df = pd.DataFrame(LIGNES, columns=["text", "attendu", "articles_ok", "critique",
                                       "difficulte"])
    for jeu in ("validation", "independant"):
        df.to_csv(d / f"jeu_{jeu}.csv", index=False)
    return d


class BouchonEval(Bouchon):
    """Ordre des mots-clés différent : « vpn on my printer » part en réseau (erreur voulue)."""

    def predire(self, texte: str, k: int = 3):  # type: ignore[no-untyped-def]
        if texte == "The printer leaks after phishing":
            return super().predire("printer")
        return super().predire(texte, k)


def test_mesures(dossier: Path) -> None:
    from support_agent.data import charger_jeu_eval

    r = evaluer.mesurer(BouchonEval(), charger_jeu_eval("validation", dossier))
    assert r["lignes"] == 8
    assert r["top1"] == 0.5 and r["top3"] == round(4 / 6, 3)  # 6 lignes informatiques
    assert r["critiques"] == {"total": 2, "manques": 1}
    assert r["hors_sujet"] == {"total": 2, "refuses": 1, "taux_refus": 0.5, "refus_a_tort": 0}
    assert r["abstention"] == round(1 / 8, 3)
    assert 0 < r["f1_macro"] < 1 and r["exactitude"] == round(5 / 8, 3)
    assert r["par_classe"]["reseau"]["rappel"] == 1.0
    assert r["par_difficulte"]["incident mêlé"] == {"lignes": 1, "exactitude": 0.0}
    assert {e["text"] for e in r["erreurs"]} == {
        "vpn on my printer", "The printer leaks after phishing", "It does not work"}
    assert len(r["matrice_confusion"]["valeurs"]) == len(r["matrice_confusion"]["etiquettes"])


def test_evaluer_validation_ecrit_le_json(dossier: Path, tmp_path: Path) -> None:
    sortie = tmp_path / "models"
    r = evaluer.evaluer(BouchonEval(), "validation", dossier=dossier, sortie=sortie,
                        trace=tmp_path / "trace.json")
    ecrit = json.loads((sortie / "eval_validation.json").read_text(encoding="utf-8"))
    for cle in ("f1_macro", "top1", "top3"):  # critère de fin de T7
        assert ecrit[cle] == r[cle]
    assert ecrit["jeu"] == "validation" and len(ecrit["empreinte_jeu"]) == 12
    evaluer.evaluer(BouchonEval(), "validation", dossier=dossier, sortie=sortie,
                    trace=tmp_path / "trace.json")  # la validation se relit librement
    assert not (tmp_path / "trace.json").exists()


def test_independant_protege(dossier: Path, tmp_path: Path) -> None:
    trace, sortie = tmp_path / "trace.json", tmp_path / "models"

    def lire(final: bool = False, relire: bool = False) -> dict:  # type: ignore[type-arg]
        return evaluer.evaluer(BouchonEval(), "independant", final, relire, dossier=dossier,
                               sortie=sortie, trace=trace)

    with pytest.raises(evaluer.LectureInterdite, match="--final"):
        lire()
    assert lire(final=True)["lecture_numero"] == 1
    with pytest.raises(evaluer.LectureInterdite, match="déjà lu"):
        lire(final=True)
    assert lire(final=True, relire=True)["lecture_numero"] == 2  # forcée, mais tracée
    assert len(json.loads(trace.read_text(encoding="utf-8"))) == 2


def test_resume_markdown(dossier: Path) -> None:
    from support_agent.data import charger_jeu_eval

    r = evaluer.mesurer(BouchonEval(), charger_jeu_eval("validation", dossier))
    r |= {"jeu": "validation", "date": "2026-11-20"}
    md = evaluer.resume(r)
    assert "| F1 macro |" in md and "| `reseau` |" in md and "| incident mêlé | 1 | 0.0 |" in md


def test_taux_sans_effectif() -> None:
    assert evaluer._taux(0, 0) is None


def test_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
              capsys: pytest.CaptureFixture[str]) -> None:
    bouchon = BouchonEval()
    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(lambda: bouchon))
    modele_factice = tmp_path / "support.joblib"
    modele_factice.write_bytes(b"x")
    monkeypatch.setattr(evaluer, "CHEMIN_MODELE", modele_factice)
    monkeypatch.setattr(evaluer, "MODELS", tmp_path)
    vrai = evaluer.evaluer

    def evaluer_tmp(*a, **kw):  # type: ignore[no-untyped-def]
        kw |= {"sortie": tmp_path, "trace": tmp_path / "trace.json"}  # jamais le vrai models/
        return vrai(*a, **kw)

    monkeypatch.setattr(evaluer, "evaluer", evaluer_tmp)
    evaluer.main(["validation"])
    sortie = capsys.readouterr().out
    assert "| F1 macro |" in sortie and "eval_validation.json" in sortie
    assert json.loads((tmp_path / "eval_validation.json").read_text("utf-8"))["modele"][
        "fichier"] == "support.joblib"
    with pytest.raises(SystemExit, match="Refusé"):
        evaluer.main(["independant"])
