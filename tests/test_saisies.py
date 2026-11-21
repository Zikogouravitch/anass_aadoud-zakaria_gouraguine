"""Saisies inhabituelles : espaces, charabia, salutations, fautes de frappe."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from support_agent.api.main import creer_app
from support_agent.config import INDETERMINE
from support_agent.conversation import (
    ACCUEIL,
    INCOMPRIS,
    Conversation,
    Etat,
    Moteur,
    est_salutation,
)
from support_agent.modele import ModeleSupport, Prediction
from support_agent.stockage import Conversations
from support_agent.tickets import Tickets
from support_agent.ui.client import ClientAPI
from tests.test_chat import Bouchon, Reglages
from tests.test_ui import APP


class BouchonCharabia(Bouchon):
    def predire(self, texte: str, k: int = 3) -> Prediction:
        if "qsd" in texte:
            self.textes.append(texte)
            return Prediction(texte, INDETERMINE, "hors_sujet", 0.9, "medium", False, [], [],
                              "incomprehensible")
        return super().predire(texte, k)


# --- salutations --------------------------------------------------------------------


@pytest.mark.parametrize(("texte", "attendu"), [
    ("hello", True), ("Hi there!", True), ("good morning", True), ("thanks", True),
    ("Hello, my VPN keeps disconnecting every hour", False), ("hellooo printer", False),
    ("My VPN drops", False),
])
def test_est_salutation(texte: str, attendu: bool) -> None:
    assert est_salutation(texte) is attendu


def test_salutation_ne_consomme_pas_la_precision() -> None:
    m, conv = Moteur(BouchonCharabia(), Tickets(None)), Conversation()
    r = m.repondre(conv, "hello")
    assert r.etat == Etat.NOUVELLE and r.message == ACCUEIL and conv.precisions == 0
    assert m.repondre(conv, "It does not work").etat == Etat.ATTENTE_PRECISION
    r = m.repondre(conv, "hi")  # pendant la précision : on reste en attente
    assert r.etat == Etat.ATTENTE_PRECISION and conv.precisions == 1
    assert m.repondre(conv, "the VPN").etat == Etat.SOLUTION_PROPOSEE


# --- charabia -------------------------------------------------------------------------


def test_charabia_redemande_sans_consommer() -> None:
    m, conv = Moteur(BouchonCharabia(), Tickets(None)), Conversation()
    r = m.repondre(conv, "qsdkjqsd lkjqsd")
    assert r.etat == Etat.NOUVELLE and r.message == INCOMPRIS
    assert conv.description == [] and conv.precisions == 0 and r.brouillon_ticket is None
    assert m.repondre(conv, "My VPN keeps disconnecting").etat == Etat.SOLUTION_PROPOSEE


def test_charabia_pendant_la_precision() -> None:
    m, conv = Moteur(BouchonCharabia(), Tickets(None)), Conversation()
    m.repondre(conv, "It does not work")
    r = m.repondre(conv, "qsd")
    assert r.etat == Etat.ATTENTE_PRECISION and r.message == INCOMPRIS
    assert conv.description == ["It does not work"]


def test_modele_charabia_et_fautes(modele: ModeleSupport,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    def proba(cat: str, p: float) -> Any:
        return lambda t, v=None: pd.DataFrame([{cat: p, "reseau": 1 - p}])

    monkeypatch.setattr(modele, "probabilites", proba("hors_sujet", 0.9))
    p = modele.predire("qsdkjqsd lkjqsd mlkjmlk")
    assert p.categorie == INDETERMINE and p.raison == "incomprehensible" and p.articles == []
    monkeypatch.setattr(modele, "probabilites", proba("materiel", 0.9))
    p = modele.predire("Prnter jamed agian")  # aucun mot connu mais catégorie IT trouvée
    assert p.categorie == "materiel" and p.raison == "" and p.articles
    monkeypatch.setattr(modele, "probabilites", lambda t, v=None: pd.DataFrame(
        [{"materiel": 0.25, "reseau": 0.25, "logiciel": 0.25, "securite": 0.25}]))
    assert modele.predire("Printer weird").raison == "confiance_faible"  # seuil de test : 0,3
    assert modele.predire("It does not work").raison == "vague"


def test_correction_des_fautes(modele: ModeleSupport) -> None:
    assert modele.corriger("printr offlin") == "printer offline"
    assert modele.corriger("asdfgh qsdkjqsd") == "asdfgh qsdkjqsd"  # charabia : inchangé
    assert modele.corriger("My VPN is down") == "My VPN is down"  # mots connus ou courts
    p = modele.predire("My printr is offlin")
    assert p.texte == "My printr is offlin" and p.texte_corrige == "My printer is offline"
    assert modele.predire("My VPN keeps disconnecting").texte_corrige == ""


# --- espaces --------------------------------------------------------------------------


def test_api_refuse_les_espaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("support_agent.api.main.get_settings", lambda: Reglages())
    c = TestClient(creer_app(Bouchon(), Conversations(None), Tickets(None)))
    for vide in ["", "   ", "\n\t  "]:
        assert c.post("/chat", json={"message": vide}).status_code == 422
    r = c.post("/chat", json={"message": "  My   VPN \n keeps   disconnecting  "})
    assert r.status_code == 200 and r.json()["article"]["id"] == "KB-NET-01"


def test_interface_ignore_les_espaces(monkeypatch: pytest.MonkeyPatch) -> None:
    appels: list[Any] = []

    def chat(self: ClientAPI, *a: Any, **kw: Any) -> dict[str, Any]:
        appels.append(a)
        return {}

    monkeypatch.setattr(ClientAPI, "chat", chat)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.chat_input[0].set_value("     ").run()
    assert appels == [] and len(at.chat_message) == 0 and not at.error


@pytest.mark.parametrize("phrase", [
    "We are still waiting for the refund you promised",  # pas « compromised »
    "A ransom note appeared on my screen",  # pas « random »
    "Someone stole my laptop",  # pas « solve »
    "The renewing of the plan failed",  # renew + ing, pas « reviewing »
    "Video calls are choppy",  # chop + p + y, pas « copy »
])
def test_correction_ne_touche_pas_les_vrais_mots(modele: ModeleSupport, phrase: str) -> None:
    assert modele.corriger(phrase) == phrase
