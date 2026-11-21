"""Tests de /chat (T5) : conversation, tentatives, question de précision, escalade proposée.

Critère de fin de T5 : ces tests passent et un incident résolu ne crée aucun ticket.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from support_agent.api.main import creer_app
from support_agent.config import HORS_SUJET, INDETERMINE
from support_agent.conversation import (
    Action,
    Conversation,
    Etat,
    Moteur,
    brouillon,
    lire_reponse,
)
from support_agent.data import charger_base
from support_agent.modele import Hyper, ModeleSupport, Prediction
from support_agent.stockage import Conversations

BASE = {a.id: a for a in charger_base()}


def art(ident: str) -> dict[str, Any]:
    a = BASE[ident]
    return {"id": a.id, "titre": a.titre, "categorie": a.categorie, "score": 0.8,
            "etapes": list(a.etapes), "escalade_si": a.escalade_si}


class Bouchon:
    """Modèle factice : la prédiction dépend de mots-clés du texte complet."""

    def __init__(self) -> None:
        self.textes: list[str] = []
        self.hyper = Hyper()

    def predire(self, texte: str, k: int = 3) -> Prediction:
        self.textes.append(texte)
        t = texte.lower()

        def p(cat: str, ids: list[str], conf: float = 0.9, critique: bool = False,
              prio: str = "medium", probable: str | None = None) -> Prediction:
            return Prediction(texte, cat, probable or cat, conf, prio, critique,
                              [art(i) for i in ids], [])

        if "weather" in t:
            return p(HORS_SUJET, [], prio="low")
        if "phishing" in t or "clicked" in t:
            return p("securite", ["KB-SEC-01", "KB-SEC-07"], critique=True, prio="high")
        if "vpn" in t:
            return p("reseau", ["KB-NET-01", "KB-NET-03", "KB-NET-08"])
        if "printer" in t:
            return p("materiel", ["KB-HW-01"])
        if "strange" in t:  # pas sûr : catégorie probable mais confiance faible
            return p(INDETERMINE, ["KB-NET-02"], conf=0.4, probable="reseau")
        return p(INDETERMINE, [], conf=0.3, probable="logiciel")  # trop vague


class Reglages:
    def __init__(self, api_key: str = "") -> None:
        self.api_key, self.seuil_abstention = api_key, 0.5


@pytest.fixture
def bouchon() -> Bouchon:
    return Bouchon()


@pytest.fixture
def journal(tmp_path: Path) -> Path:
    return tmp_path / "tickets" / "conversations.jsonl"


@pytest.fixture
def client(bouchon: Bouchon, journal: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages())
    return TestClient(creer_app(bouchon, Conversations(journal)))


def chat(c: TestClient, **corps: Any) -> dict[str, Any]:
    r = c.post("/chat", json=corps)
    assert r.status_code == 200, r.text
    donnees: dict[str, Any] = r.json()
    return donnees


# --- parcours de la version minimale ---------------------------------------------


def test_parcours_minimal_vpn_deux_echecs_puis_escalade(client: TestClient) -> None:
    r1 = chat(client, message="My VPN keeps disconnecting every 10 minutes")
    cid = r1["conversation_id"]
    assert r1["etat"] == "solution_proposee"
    assert r1["prediction"]["categorie"] == "reseau"
    assert r1["article"]["id"] == "KB-NET-01" and r1["tentative"] == 1
    assert "Did this solve your problem?" in r1["message"]
    assert r1["actions"] == ["resolu", "non_resolu", "technicien"]

    r2 = chat(client, conversation_id=cid, action="non_resolu")
    assert r2["etat"] == "solution_proposee"
    assert r2["article"]["id"] == "KB-NET-03" and r2["tentative"] == 2

    r3 = chat(client, conversation_id=cid, action="non_resolu")
    assert r3["etat"] == "escalade_proposee"
    b = r3["brouillon_ticket"]
    assert b["categorie"] == "reseau" and b["motif"] == "non_resolu_apres_essais"
    assert b["articles_essayes"] == ["KB-NET-01", "KB-NET-03"]
    assert b["conversation_id"] == cid and "VPN" in b["description"]
    assert r3["actions"] == ["confirmer_ticket", "annuler"]


def test_incident_resolu_ne_cree_aucun_ticket(client: TestClient, journal: Path) -> None:
    r1 = chat(client, message="My VPN keeps disconnecting")
    r2 = chat(client, conversation_id=r1["conversation_id"], action="resolu")
    assert r2["etat"] == "resolue"
    assert r2["brouillon_ticket"] is None
    assert "No ticket was created" in r2["message"]
    assert not (journal.parent / "tickets.jsonl").exists()
    etats = [json.loads(ligne)["etat"] for ligne in journal.read_text("utf-8").splitlines()]
    assert etats == ["solution_proposee", "resolue"]


# --- réponses libres -------------------------------------------------------------


@pytest.mark.parametrize(("texte", "etat"), [
    ("It works now, thanks!", "resolue"),
    ("yes", "resolue"),
    ("No, it still disconnects", "solution_proposee"),
    ("I want to talk to a technician", "escalade_proposee"),
])
def test_reponse_libre(client: TestClient, texte: str, etat: str) -> None:
    r1 = chat(client, message="My VPN keeps disconnecting")
    r2 = chat(client, conversation_id=r1["conversation_id"], message=texte)
    assert r2["etat"] == etat


def test_nouveau_probleme_dans_la_meme_conversation(client: TestClient) -> None:
    r1 = chat(client, message="My VPN keeps disconnecting")
    r2 = chat(client, conversation_id=r1["conversation_id"],
              message="Also the printer on the 2nd floor is jammed and shows an error")
    assert r2["prediction"]["categorie"] == "materiel" and r2["tentative"] == 1


# --- précision, hors sujet, cas critique -----------------------------------------


def test_question_de_precision_puis_solution(client: TestClient, bouchon: Bouchon) -> None:
    r1 = chat(client, message="It does not work")
    assert r1["etat"] == "attente_precision"
    assert "more detail" in r1["message"]
    r2 = chat(client, conversation_id=r1["conversation_id"], message="the VPN, since today")
    assert r2["etat"] == "solution_proposee" and r2["article"]["id"] == "KB-NET-01"
    assert bouchon.textes[-1] == "It does not work the VPN, since today"  # texte cumulé


def test_precision_ciblee_selon_la_categorie_probable(client: TestClient) -> None:
    r = chat(client, message="Something strange happens")
    assert r["etat"] == "attente_precision"
    assert "Wi-Fi, the VPN or the network cable" in r["message"]


def test_toujours_indetermine_apres_precision(client: TestClient) -> None:
    r1 = chat(client, message="It does not work")
    r2 = chat(client, conversation_id=r1["conversation_id"], message="it is broken")
    assert r2["etat"] == "escalade_proposee"
    assert r2["brouillon_ticket"]["motif"] == "categorie_indeterminee"
    assert r2["brouillon_ticket"]["categorie"] == INDETERMINE


def test_technicien_pendant_la_precision(client: TestClient) -> None:
    r1 = chat(client, message="It does not work")
    r2 = chat(client, conversation_id=r1["conversation_id"], message="get me a technician")
    assert r2["etat"] == "escalade_proposee"
    assert r2["brouillon_ticket"]["motif"] == "demande_utilisateur"


def test_hors_sujet(client: TestClient) -> None:
    r = chat(client, message="What's the weather tomorrow?")
    assert r["etat"] == "hors_sujet" and r["actions"] == [] and r["brouillon_ticket"] is None
    assert "only help with IT problems" in r["message"]


def test_cas_critique_escalade_immediate(client: TestClient) -> None:
    r = chat(client, message="I clicked a phishing link and typed my password")
    assert r["etat"] == "escalade_proposee" and r["tentative"] == 0
    assert r["article"]["id"] == "KB-SEC-01"
    assert "Do not click any link" in r["message"]  # étapes de sécurité affichées
    b = r["brouillon_ticket"]
    assert b["motif"] == "cas_critique" and b["priorite"] == "high" and b["critique"]
    assert b["articles_essayes"] == ["KB-SEC-01"]


# --- après une escalade proposée -------------------------------------------------


def test_escalade_annulee(client: TestClient) -> None:
    r1 = chat(client, message="I clicked a phishing link")
    r2 = chat(client, conversation_id=r1["conversation_id"], action="annuler")
    assert r2["etat"] == "fermee" and "no ticket was created" in r2["message"]


def test_escalade_oui_libre_ne_cree_rien(client: TestClient) -> None:
    r1 = chat(client, message="I clicked a phishing link")
    r2 = chat(client, conversation_id=r1["conversation_id"], message="yes please")
    assert r2["etat"] == "escalade_proposee" and "Create ticket" in r2["message"]
    r3 = chat(client, conversation_id=r1["conversation_id"], message="no")
    assert r3["etat"] == "fermee"


def test_plus_d_article_disponible(client: TestClient) -> None:
    r1 = chat(client, message="The printer is jammed")  # un seul article candidat
    r2 = chat(client, conversation_id=r1["conversation_id"], action="non_resolu")
    assert r2["etat"] == "escalade_proposee"


# --- erreurs et sécurité ---------------------------------------------------------


def test_erreurs_de_requete(client: TestClient) -> None:
    assert client.post("/chat", json={}).status_code == 422
    assert client.post("/chat", json={"message": "   "}).status_code == 422
    assert client.post("/chat", json={"action": "resolu"}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 2001}).status_code == 422
    r = client.post("/chat", json={"conversation_id": "inconnue", "message": "hi"})
    assert r.status_code == 404


def test_cle_api(bouchon: Bouchon, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages("secret"))
    c = TestClient(creer_app(bouchon, Conversations(None)))
    assert c.post("/chat", json={"message": "vpn"}).status_code == 401
    assert c.post("/chat", json={"message": "vpn"},
                  headers={"X-API-Key": "faux"}).status_code == 401
    assert c.post("/chat", json={"message": "vpn"},
                  headers={"X-API-Key": "secret"}).status_code == 200
    assert c.get("/health").status_code == 200  # /health reste ouvert


def test_health_et_predict(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "modele_charge": True,
                                            "version": "0.1.0"}
    r = client.post("/predict", json={"text": "My VPN keeps disconnecting"})
    assert r.status_code == 200 and r.json()["articles"][0]["id"] == "KB-NET-01"
    assert client.post("/predict", json={"text": "  "}).status_code == 422


def test_modele_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    def absent() -> ModeleSupport:
        raise FileNotFoundError("models/support.joblib absent : lancer support_agent.train")

    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(absent))
    c = TestClient(creer_app(None, Conversations(None)))
    assert c.get("/health").json()["modele_charge"] is False
    r = c.post("/chat", json={"message": "vpn"})
    assert r.status_code == 503 and "support_agent.train" in r.json()["detail"]


def test_modele_charge_au_premier_appel(monkeypatch: pytest.MonkeyPatch,
                                        bouchon: Bouchon) -> None:
    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(lambda: bouchon))
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages())
    c = TestClient(creer_app(None, Conversations(None)))
    assert chat(c, message="My VPN drops")["etat"] == "solution_proposee"
    assert c.get("/health").json()["modele_charge"] is True
    assert bouchon.textes[0].startswith("warm up")  # préchauffage avant le 1er message


def test_prechargement_au_demarrage(monkeypatch: pytest.MonkeyPatch, bouchon: Bouchon) -> None:
    import time

    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(lambda: bouchon))
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages())
    with TestClient(creer_app(None, Conversations(None))) as c:  # déclenche le démarrage
        for _ in range(50):
            if c.get("/health").json()["modele_charge"]:
                break
            time.sleep(0.05)
        assert c.get("/health").json()["modele_charge"] is True


def test_prechargement_sans_modele(monkeypatch: pytest.MonkeyPatch) -> None:
    def absent() -> ModeleSupport:
        raise FileNotFoundError("absent")

    monkeypatch.setattr(ModeleSupport, "charger", staticmethod(absent))
    with TestClient(creer_app(None, Conversations(None))) as c:
        assert c.get("/health").json()["status"] == "ok"  # l'API démarre quand même


# --- moteur seul -----------------------------------------------------------------


@pytest.mark.parametrize(("texte", "action"), [
    ("thanks, solved", Action.RESOLU), ("ok", Action.RESOLU),
    ("nope", Action.NON_RESOLU), ("it doesn't work", Action.NON_RESOLU),
    ("please open a ticket", Action.TECHNICIEN),
    ("My printer on the third floor shows an error code and I cannot print anything", None),
    ("Thanks but it still does not work at all, the VPN drops again every few minutes",
     Action.NON_RESOLU),
    ("The keyboard", None),
])
def test_lire_reponse(texte: str, action: Action | None) -> None:
    assert lire_reponse(texte) is action


def test_moteur_sans_message_ni_action(bouchon: Bouchon) -> None:
    with pytest.raises(ValueError):
        Moteur(bouchon).repondre(Conversation())


def test_moteur_action_sans_incident(bouchon: Bouchon) -> None:
    rep = Moteur(bouchon).repondre(Conversation(), action=Action.TECHNICIEN)
    assert rep.etat == Etat.NOUVELLE and "describe" in rep.message


def test_brouillon_sans_prediction() -> None:
    b = brouillon(Conversation())
    assert b["categorie"] == INDETERMINE and b["priorite"] == "medium" and b["motif"] is None


def test_historique(bouchon: Bouchon) -> None:
    conv = Conversation()
    Moteur(bouchon).repondre(conv, "My VPN keeps disconnecting")
    assert [t.role for t in conv.historique] == ["utilisateur", "agent"]
    assert conv.en_dict()["etat"] == Etat.SOLUTION_PROPOSEE


def test_stockage(tmp_path: Path) -> None:
    s = Conversations(tmp_path / "c.jsonl")
    conv = s.nouvelle()
    assert s.obtenir(conv.id) is conv and s.obtenir("x") is None and len(s) == 1
    s.enregistrer(conv)
    assert json.loads((tmp_path / "c.jsonl").read_text("utf-8"))["id"] == conv.id
    Conversations(None).enregistrer(conv)  # sans journal : ne fait rien


# --- avec le vrai modèle (entraîné sur le petit jeu de conftest) -----------------


def test_chat_avec_vrai_modele(modele: ModeleSupport) -> None:
    c = TestClient(creer_app(modele, Conversations(None)))
    r = chat(c, message="My VPN keeps disconnecting")
    assert r["prediction"]["categorie"] == "reseau" and r["article"]["id"] == "KB-NET-01"
