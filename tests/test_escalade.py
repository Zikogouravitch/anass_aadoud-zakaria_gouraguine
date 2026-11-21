"""Tests de T6 : règles d'escalade une à une, tickets, /tickets, bilan des 30 conversations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from support_agent import bilan_tickets
from support_agent.api.main import creer_app
from support_agent.config import INDETERMINE
from support_agent.conversation import Action, Conversation, Etat, Moteur
from support_agent.escalade import (
    GROUPES,
    Motif,
    apres_echec,
    delai,
    exige_technicien,
    groupe,
    motif_immediat,
    priorite_ticket,
)
from support_agent.stockage import Conversations
from support_agent.tickets import Statut, Tickets
from tests.test_chat import Bouchon, Reglages, art

# --- règles, une à une ------------------------------------------------------------


def test_r1_cas_critique() -> None:
    assert motif_immediat("securite", True, art("KB-SEC-01")) == Motif.CRITIQUE
    assert motif_immediat("compte_acces", True, art("KB-ACC-06")) == Motif.CRITIQUE


def test_r2_article_always() -> None:
    assert exige_technicien(art("KB-ACC-08"))  # « always: accounts ... are created by »
    assert exige_technicien(art("KB-BIL-03"))  # « always for a refund »
    assert not exige_technicien(art("KB-NET-01"))
    assert not exige_technicien(None)
    assert motif_immediat("compte_acces", False, art("KB-ACC-08")) == Motif.ARTICLE


def test_pas_d_escalade_immediate() -> None:
    assert motif_immediat("reseau", False, art("KB-NET-01")) is None
    assert motif_immediat(INDETERMINE, True, art("KB-SEC-01")) is None  # précision d'abord
    assert motif_immediat("hors_sujet", False, None) is None


def test_r3_apres_echec() -> None:
    assert not apres_echec(1, reste_un_article=True)
    assert apres_echec(2, reste_un_article=True)
    assert apres_echec(1, reste_un_article=False)


def test_groupes_et_delais() -> None:
    assert groupe("securite") == "Security team"
    assert groupe(INDETERMINE) == groupe(None) == groupe("inconnue") == GROUPES[INDETERMINE]
    assert delai("high") == "4 hours" and delai("??") == "1 business day"


def test_priorite_ticket() -> None:
    assert priorite_ticket("low", True, None) == "high"
    assert priorite_ticket("low", False, Motif.CRITIQUE) == "high"
    assert priorite_ticket("low", False, Motif.ECHECS) == "low"
    assert priorite_ticket(None, False, None) == "medium"


# --- stockage des tickets ---------------------------------------------------------


def _brouillon(**kw: Any) -> dict[str, Any]:
    b: dict[str, Any] = {"conversation_id": "c1", "categorie": "reseau",
                         "categorie_probable": "reseau", "priorite": "medium",
                         "critique": False, "motif": "non_resolu_apres_essais",
                         "description": "VPN drops", "articles_essayes": ["KB-NET-01"],
                         "tentatives": 2}
    b.update(kw)
    return b


def test_tickets_creation_identifiant_et_relecture(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    s = Tickets(f)
    t1 = s.creer(_brouillon())
    assert t1.id == "INC-00001" and t1.groupe == "Network" and t1.statut == Statut.OUVERT
    assert t1.delai == "1 business day"
    assert s.creer(_brouillon()).id == "INC-00001"  # même incident : pas de doublon
    t2 = s.creer(_brouillon(conversation_id="c2", critique=True, categorie="securite"))
    assert t2.id == "INC-00002" and t2.priorite == "high" and t2.groupe == "Security team"
    s.changer_statut("INC-00001", Statut.EN_COURS, "on it")
    relu = Tickets(f)  # rechargement depuis le fichier : la dernière ligne fait foi
    assert len(relu) == 2
    t = relu.obtenir("inc-00001")
    assert t is not None and t.statut == Statut.EN_COURS and t.note == "on it"


def test_tickets_liste_critiques_en_tete() -> None:
    s = Tickets(None)
    s.creer(_brouillon(conversation_id="a", priorite="low"))
    s.creer(_brouillon(conversation_id="b", critique=True))
    s.creer(_brouillon(conversation_id="c", priorite="high"))
    assert [t.conversation_id for t in s.lister()] == ["b", "c", "a"]
    assert s.lister(Statut.RESOLU) == []
    assert s.changer_statut("INC-99999", Statut.RESOLU) is None
    assert s.par_conversation("zzz") is None


def test_nouvel_incident_meme_conversation_nouveau_ticket() -> None:
    s = Tickets(None)
    s.creer(_brouillon())
    assert s.creer(_brouillon(description="printer jam")).id == "INC-00002"


# --- moteur : confirmation ---------------------------------------------------------


def test_confirmation_cree_le_ticket() -> None:
    m = Moteur(Bouchon(), Tickets(None))
    conv = Conversation()
    m.repondre(conv, "I clicked a phishing link")
    rep = m.repondre(conv, action=Action.CONFIRMER)
    assert rep.etat == Etat.TICKET_CREE and rep.ticket is not None
    assert rep.ticket["id"] == conv.ticket_id == "INC-00001"
    assert "Security team" in rep.message and "4 hours" in rep.message
    again = m.repondre(conv, action=Action.TECHNICIEN)  # rappel, pas de doublon
    assert again.ticket is not None and again.ticket["id"] == "INC-00001"


def test_confirmation_impossible_sans_escalade() -> None:
    m = Moteur(Bouchon(), Tickets(None))
    conv = Conversation()
    m.repondre(conv, "My VPN keeps disconnecting")
    rep = m.repondre(conv, action=Action.CONFIRMER)
    assert rep.etat == Etat.SOLUTION_PROPOSEE and rep.ticket is None


def test_confirmation_sans_stockage() -> None:
    m = Moteur(Bouchon())
    conv = Conversation()
    m.repondre(conv, "I clicked a phishing link")
    with pytest.raises(RuntimeError):
        m.repondre(conv, action=Action.CONFIRMER)


def test_article_always_escalade_tout_de_suite() -> None:
    class Compte(Bouchon):
        def predire(self, texte: str, k: int = 3) -> Any:
            p = super().predire("vpn")
            p.categorie = p.categorie_probable = "compte_acces"
            p.articles = [art("KB-ACC-08")]
            return p

    rep = Moteur(Compte(), Tickets(None)).repondre(Conversation(), "Create an account")
    assert rep.etat == Etat.ESCALADE_PROPOSEE and rep.tentative == 0
    assert rep.brouillon_ticket is not None
    assert rep.brouillon_ticket["motif"] == "article_exige_technicien"
    assert rep.brouillon_ticket["groupe"] == "Identity & access"
    assert "prepare the following" in rep.message


# --- API /tickets -----------------------------------------------------------------


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages())
    return TestClient(creer_app(Bouchon(), Conversations(None), Tickets(tmp_path / "t.jsonl")))


def _post(c: TestClient, chemin: str, **corps: Any) -> Any:
    return c.post(chemin, json=corps)


def test_api_parcours_minimal_jusqu_a_l_identifiant(api: TestClient) -> None:
    """Le parcours de la version minimale : VPN, 2 échecs, ticket confirmé, identifiant."""
    cid = _post(api, "/chat", message="My VPN keeps disconnecting").json()["conversation_id"]
    _post(api, "/chat", conversation_id=cid, action="non_resolu")
    r = _post(api, "/chat", conversation_id=cid, action="non_resolu").json()
    assert r["etat"] == "escalade_proposee"
    assert r["brouillon_ticket"]["groupe"] == "Network"
    creation = _post(api, "/tickets", conversation_id=cid)
    assert creation.status_code == 201
    t = creation.json()
    assert t["id"] == "INC-00001" and t["articles_essayes"] == ["KB-NET-01", "KB-NET-03"]
    suivi = api.get("/tickets/INC-00001").json()
    assert suivi["statut"] == "ouvert" and suivi["conversation_id"] == cid
    assert _post(api, "/tickets", conversation_id=cid).json()["id"] == "INC-00001"


def test_api_confirmation_par_chat(api: TestClient) -> None:
    cid = _post(api, "/chat", message="I clicked a phishing link").json()["conversation_id"]
    r = _post(api, "/chat", conversation_id=cid, action="confirmer_ticket").json()
    assert r["etat"] == "ticket_cree" and r["ticket"]["priorite"] == "high"


def test_api_ticket_refuse_sans_escalade(api: TestClient) -> None:
    cid = _post(api, "/chat", message="My VPN keeps disconnecting").json()["conversation_id"]
    r = _post(api, "/tickets", conversation_id=cid)
    assert r.status_code == 409
    assert _post(api, "/tickets", conversation_id="inconnue").status_code == 404
    assert _post(api, "/tickets").status_code == 422


def test_api_suivi_liste_et_maj(api: TestClient) -> None:
    for msg in ["I clicked a phishing link", "My VPN keeps disconnecting"]:
        cid = _post(api, "/chat", message=msg).json()["conversation_id"]
        _post(api, "/chat", conversation_id=cid, action="technicien")
        _post(api, "/tickets", conversation_id=cid)
    liste = api.get("/tickets").json()
    assert [t["categorie"] for t in liste] == ["securite", "reseau"]
    assert api.get("/tickets", params={"statut": "resolu"}).json() == []
    assert api.get("/tickets", params={"limite": 0}).status_code == 422
    r = api.patch("/tickets/inc-00002", json={"statut": "resolu", "note": "VPN profile reset"})
    assert r.status_code == 200 and r.json()["statut"] == "resolu"
    assert api.get("/tickets/INC-00002").json()["note"] == "VPN profile reset"
    assert api.get("/tickets/INC-00404").status_code == 404
    assert api.patch("/tickets/INC-00404", json={"statut": "resolu"}).status_code == 404
    assert api.patch("/tickets/INC-00001", json={"statut": "perdu"}).status_code == 422


# --- bilan des 30 conversations ----------------------------------------------------


def test_jeu_de_30_conversations() -> None:
    scenarios = bilan_tickets.charger_conversations()
    assert len(scenarios) == 30
    assert sum(s["attendu"]["ticket"] for s in scenarios) == 10
    assert len({s["id"] for s in scenarios}) == 30


def test_jeu_conversations_invalide(tmp_path: Path) -> None:
    f = tmp_path / "c.json"
    f.write_text(json.dumps([{"id": "X", "tours": [{"message": "a", "action": "resolu"}]}]))
    with pytest.raises(ValueError):
        bilan_tickets.charger_conversations(f)
    f.write_text(json.dumps([{"id": "X", "tours": [{"action": "danser"}]}]))
    with pytest.raises(ValueError):
        bilan_tickets.charger_conversations(f)


def test_bilan_avec_bouchon() -> None:
    scenarios = [
        {"id": "A", "role": "r", "tours": [{"message": "I clicked a phishing link"},
                                           {"action": "confirmer_ticket"}],
         "attendu": {"ticket": True, "categorie": "securite", "motif": "cas_critique"}},
        {"id": "B", "role": "r", "tours": [{"message": "My VPN drops"}, {"action": "resolu"}],
         "attendu": {"ticket": False, "etat": "resolue"}},
        {"id": "C", "role": "r", "tours": [{"message": "My VPN drops"},
                                           {"action": "technicien"},
                                           {"action": "confirmer_ticket"}],
         "attendu": {"ticket": False, "etat": "resolue"}},  # ticket en trop
    ]
    res = bilan_tickets.bilan(Bouchon(), scenarios)
    assert res["tickets_crees"] == 2 and res["tickets_corrects"] == 1
    assert res["tickets_en_trop"] == 1 and res["tickets_manques"] == 0
    assert [d["correct"] for d in res["details"]] == [True, True, False]


def test_bilan_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                    capsys: pytest.CaptureFixture[str]) -> None:
    from support_agent.modele import ModeleSupport

    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(lambda: Bouchon()))
    sortie = tmp_path / "bilan.json"
    bilan_tickets.main(["--sortie", str(sortie)])
    res = json.loads(sortie.read_text(encoding="utf-8"))
    assert res["conversations"] == 30
    assert "tickets créés" in capsys.readouterr().out
