"""Interface (onglet Chat) et client HTTP, sans API réelle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from support_agent.ui.client import ClientAPI, ErreurAPI

APP = str(Path(__file__).resolve().parent.parent / "support_agent" / "ui" / "app.py")


# --- client ----------------------------------------------------------------------


def _client(gestion: Any) -> ClientAPI:
    return ClientAPI("http://api", cle="k", transport=httpx.MockTransport(gestion))


def test_client_chat_envoie_seulement_les_champs_remplis() -> None:
    vus: list[httpx.Request] = []

    def gestion(req: httpx.Request) -> httpx.Response:
        vus.append(req)
        return httpx.Response(200, json={"conversation_id": "c1", "etat": "x"})

    c = _client(gestion)
    assert c.chat("VPN down")["conversation_id"] == "c1"
    assert json.loads(vus[0].content) == {"message": "VPN down"}
    assert vus[0].headers["X-API-Key"] == "k"
    c.chat(conversation_id="c1", action="resolu")
    assert json.loads(vus[1].content) == {"conversation_id": "c1", "action": "resolu"}


def test_client_sante() -> None:
    c = _client(lambda req: httpx.Response(200, json={"status": "ok"}))
    assert c.sante() == {"status": "ok"}


def test_client_erreurs() -> None:
    with pytest.raises(ErreurAPI, match="404 : conversation inconnue"):
        _client(lambda r: httpx.Response(404, json={"detail": "conversation inconnue"})).chat("x")
    with pytest.raises(ErreurAPI, match="500 : boom"):
        _client(lambda r: httpx.Response(500, text="boom")).chat("x")

    def panne(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refusé")

    with pytest.raises(ErreurAPI, match="injoignable"):
        _client(panne).chat("x")


# --- application Streamlit -------------------------------------------------------

REPONSES: dict[str | None, dict[str, Any]] = {
    None: {"conversation_id": "c1", "etat": "solution_proposee",
           "message": "Let's try this (KB-NET-01):\n1. Restart\n\nDid this solve your problem?",
           "prediction": {"categorie": "reseau", "confiance": 0.95, "priorite": "medium",
                          "critique": False},
           "tentative": 1, "actions": ["resolu", "non_resolu", "technicien"],
           "brouillon_ticket": None},
    "technicien": {"conversation_id": "c1", "etat": "escalade_proposee",
                   "message": "Sure, I can open a ticket for a technician.",
                   "prediction": {"categorie": "reseau", "confiance": 0.95, "priorite": "high",
                                  "critique": True},
                   "tentative": 1, "actions": ["confirmer_ticket", "annuler"],
                   "brouillon_ticket": {"categorie": "reseau", "priorite": "high",
                                        "motif": "demande_utilisateur",
                                        "articles_essayes": ["KB-NET-01"],
                                        "description": "VPN drops"}},
}


@pytest.fixture
def faux_chat(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    appels: list[tuple[Any, ...]] = []

    def chat(self: ClientAPI, message: str | None = None, conversation_id: str | None = None,
             action: str | None = None) -> dict[str, Any]:
        appels.append((message, conversation_id, action))
        return REPONSES[action]

    monkeypatch.setattr(ClientAPI, "chat", chat)
    return appels


def test_app_conversation(faux_chat: list[tuple[Any, ...]]) -> None:
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert at.title[0].value == "IT support agent"
    at.chat_input[0].set_value("My VPN drops").run()
    assert faux_chat[0] == ("My VPN drops", None, None)
    textes = [m.markdown[0].value for m in at.chat_message]
    assert textes[0] == "My VPN drops" and "KB-NET-01" in textes[1]
    assert any("Category **reseau**" in c.value for c in at.caption)
    boutons = [b.label for b in at.button]
    assert "✅ Solved" in boutons and "🧑‍🔧 Talk to a technician" in boutons

    next(b for b in at.button if b.label.startswith("🧑")).click().run()
    assert faux_chat[1] == (None, "c1", "technicien")
    assert at.table[0].value is not None  # brouillon de ticket affiché
    assert ":red[**critical**]" in " ".join(c.value for c in at.caption)

    at.sidebar.button[0].click().run()  # nouvelle conversation
    assert len(at.chat_message) == 0


def test_app_api_injoignable(monkeypatch: pytest.MonkeyPatch) -> None:
    def panne(self: ClientAPI, *a: Any, **kw: Any) -> dict[str, Any]:
        raise ErreurAPI("API injoignable (http://x)")

    monkeypatch.setattr(ClientAPI, "chat", panne)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value("hello").run()
    assert "API injoignable" in at.error[0].value
