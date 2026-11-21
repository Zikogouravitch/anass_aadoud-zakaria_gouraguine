"""Application FastAPI.

    uvicorn support_agent.api.main:app --reload      # http://localhost:8000/docs

Si `API_KEY` est défini dans .env, chaque appel (sauf /health) doit envoyer l'en-tête
`X-API-Key`.
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status

from support_agent import __version__
from support_agent.api.schemas import (
    ChatReponse,
    ChatRequete,
    MajTicket,
    PredictReponse,
    PredictRequete,
    Sante,
    TicketCreation,
    TicketReponse,
)
from support_agent.config import get_settings
from support_agent.conversation import Action, Conversation, Etat, Modele, Moteur
from support_agent.modele import ModeleSupport
from support_agent.stockage import Conversations
from support_agent.tickets import Statut, Tickets


class Services:
    """Modèle, conversations et tickets, partagés par l'application.

    Le modèle (torch + MiniLM + base encodée) met ~30 s à charger : il est préchargé en
    arrière-plan au démarrage, sinon au premier appel.
    """

    def __init__(self, modele: Modele | None = None,
                 conversations: Conversations | None = None,
                 tickets: Tickets | None = None) -> None:
        self._modele = modele
        self._verrou = threading.Lock()
        self.conversations = conversations if conversations is not None else Conversations()
        self.tickets = tickets if tickets is not None else Tickets()

    @property
    def modele_charge(self) -> bool:
        return self._modele is not None

    @property
    def modele(self) -> Modele:
        with self._verrou:
            if self._modele is None:
                try:
                    m = ModeleSupport.charger()
                except FileNotFoundError as e:
                    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
                m.hyper = type(m.hyper)(**{**m.hyper.__dict__,
                                           "seuil": get_settings().seuil_abstention})
                m.predire("warm up: my VPN does not connect")  # charge MiniLM et la base
                self._modele = m
            return self._modele

    def precharger(self) -> None:
        # modèle absent : on ne bloque pas le démarrage, l'erreur 503 sera renvoyée à l'appel
        with suppress(HTTPException):
            _ = self.modele

    def conversation(self, ident: str) -> Conversation:
        conv = self.conversations.obtenir(ident)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation inconnue")
        return conv


def verifier_cle(x_api_key: Annotated[str | None, Header()] = None) -> None:
    attendue = get_settings().api_key
    if attendue and not (x_api_key and secrets.compare_digest(x_api_key, attendue)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "clé API absente ou invalide")


def services(request: Request) -> Services:
    s: Services = request.app.state.services
    return s


ServicesDep = Annotated[Services, Depends(services)]


def creer_app(modele: Modele | None = None, conversations: Conversations | None = None,
              tickets: Tickets | None = None) -> FastAPI:
    svc = Services(modele, conversations, tickets)

    @asynccontextmanager
    async def cycle_de_vie(_: FastAPI) -> AsyncIterator[None]:
        if not svc.modele_charge:
            threading.Thread(target=svc.precharger, daemon=True).start()
        yield

    app = FastAPI(title="Agent_support_info", version=__version__, lifespan=cycle_de_vie,
                  description="Agent de support informatique de premier niveau.")
    app.state.services = svc
    protege = [Depends(verifier_cle)]

    @app.get("/health", response_model=Sante)
    def sante(s: ServicesDep) -> Sante:
        return Sante(status="ok", modele_charge=s.modele_charge, version=__version__)

    @app.post("/predict", response_model=PredictReponse, dependencies=protege)
    def predire(req: PredictRequete, s: ServicesDep) -> PredictReponse:
        """Classement seul d'un message (sans conversation)."""
        return PredictReponse(**s.modele.predire(req.text).en_dict())

    @app.post("/chat", response_model=ChatReponse, dependencies=protege)
    def chat(req: ChatRequete, s: ServicesDep) -> ChatReponse:
        """Un tour de conversation : un message libre ou une action (resolu, non_resolu,
        technicien, confirmer_ticket, annuler)."""
        conv = (s.conversations.nouvelle() if req.conversation_id is None
                else s.conversation(req.conversation_id))
        rep = Moteur(s.modele, s.tickets).repondre(conv, req.message, req.action)
        s.conversations.enregistrer(conv)
        return ChatReponse(**asdict(rep))

    @app.post("/tickets", response_model=TicketReponse, status_code=status.HTTP_201_CREATED,
              dependencies=protege)
    def creer_ticket(req: TicketCreation, s: ServicesDep) -> TicketReponse:
        """Crée le ticket pré-rempli d'une conversation, après confirmation de l'employé.

        Seule une conversation dont l'escalade a été proposée peut produire un ticket ;
        un second appel renvoie le même ticket (pas de doublon)."""
        conv = s.conversation(req.conversation_id)
        if conv.etat not in {Etat.ESCALADE_PROPOSEE, Etat.TICKET_CREE}:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"aucune escalade proposée dans cette conversation "
                                f"(état : {conv.etat})")
        rep = Moteur(s.modele, s.tickets).repondre(conv, action=Action.CONFIRMER)
        s.conversations.enregistrer(conv)
        assert rep.ticket is not None
        return TicketReponse(**rep.ticket)

    @app.get("/tickets/{ident}", response_model=TicketReponse, dependencies=protege)
    def suivre_ticket(ident: str, s: ServicesDep) -> TicketReponse:
        """Suivi d'un ticket par son identifiant (INC-00001)."""
        t = s.tickets.obtenir(ident)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket inconnu")
        return TicketReponse(**t.en_dict())

    @app.get("/tickets", response_model=list[TicketReponse], dependencies=protege)
    def lister_tickets(s: ServicesDep, statut: Statut | None = None,
                       limite: Annotated[int, Query(ge=1, le=1000)] = 100
                       ) -> list[TicketReponse]:
        """Tickets pour les techniciens : cas critiques et priorité haute en tête."""
        return [TicketReponse(**t.en_dict()) for t in s.tickets.lister(statut, limite)]

    @app.patch("/tickets/{ident}", response_model=TicketReponse, dependencies=protege)
    def maj_ticket(ident: str, req: MajTicket, s: ServicesDep) -> TicketReponse:
        """Mise à jour par un technicien : statut et note."""
        t = s.tickets.changer_statut(ident.strip().upper(), req.statut, req.note)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket inconnu")
        return TicketReponse(**t.en_dict())

    return app


app = creer_app()
