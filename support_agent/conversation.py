"""Moteur de conversation de l'agent (sans FastAPI, donc facile à tester).

Parcours d'un incident :

    nouveau message ──► hors sujet ? ──► refus poli
          │
          ├─► trop vague / pas sûr ──► question de précision (1 fois) ──► sinon tri humain
          ├─► cas critique ou article « always » ──► étapes + escalade proposée tout de suite
          └─► solution proposée (essai 1) ──► « résolu » ──► fermé, aucun ticket
                       │ « pas résolu »
                       ▼
                  essai 2 (article suivant) ──► « pas résolu » ──► escalade proposée

L'escalade produit un brouillon de ticket pré-rempli ; le ticket n'est créé qu'après
confirmation explicite de l'employé (action `confirmer_ticket`). Les règles d'escalade
sont dans `escalade.py`.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from support_agent.config import HORS_SUJET, INDETERMINE
from support_agent.escalade import (
    Motif,
    apres_echec,
    delai,
    groupe,
    motif_immediat,
    priorite_ticket,
)
from support_agent.modele import Prediction
from support_agent.tickets import Tickets

MAX_PRECISIONS = 1


class Modele(Protocol):
    def predire(self, texte: str, k: int = 3) -> Prediction: ...


class Etat(StrEnum):
    NOUVELLE = "nouvelle"
    ATTENTE_PRECISION = "attente_precision"
    SOLUTION_PROPOSEE = "solution_proposee"
    ESCALADE_PROPOSEE = "escalade_proposee"
    TICKET_CREE = "ticket_cree"
    RESOLUE = "resolue"
    HORS_SUJET = "hors_sujet"
    FERMEE = "fermee"


class Action(StrEnum):
    RESOLU = "resolu"
    NON_RESOLU = "non_resolu"
    TECHNICIEN = "technicien"
    CONFIRMER = "confirmer_ticket"
    ANNULER = "annuler"


# --- lecture des réponses libres (« it works now », « still broken », ...) -------------

_TECHNICIEN = re.compile(
    r"\b(?:technician|human|real person|someone from it|it team|support team|agent"
    r"|open a ticket|create a ticket|a ticket|escalate|call me)\b", re.I)
_NEGATIF = re.compile(
    r"\b(?:no|nope|not|still|didn'?t|doesn'?t|isn'?t|won'?t|can'?t|cannot|nothing|same"
    r"|again|worse)\b", re.I)
_POSITIF = re.compile(
    r"\b(?:yes|yep|works?|worked|working|fixed|solved|resolved|thanks?|thank you|great"
    r"|perfect|ok|okay|good)\b", re.I)


def lire_reponse(message: str) -> Action | None:
    """Interprète une réponse courte à « Did this solve your problem? »."""
    m = message.strip()
    if _TECHNICIEN.search(m):
        return Action.TECHNICIEN
    if len(m.split()) > 12:  # une longue phrase décrit plutôt un (nouveau) problème
        return Action.NON_RESOLU if _NEGATIF.search(m) and _POSITIF.search(m) else None
    if _NEGATIF.search(m):
        return Action.NON_RESOLU
    if _POSITIF.search(m):
        return Action.RESOLU
    return None


_SALUTATION = re.compile(
    r"^\W*(?:hi|hello|hey|good (?:morning|afternoon|evening)|bonjour|salut|salam|"
    r"thanks?|thank you|ok|okay)\b[\w\s!.,?]{0,20}$", re.I)

ACCUEIL = ("Hello! I'm the level-1 IT support assistant. Describe your problem in a "
           "sentence, for example: « My VPN keeps disconnecting » or « The printer is "
           "offline ».")
INCOMPRIS = ("Sorry, I didn't understand your message. Please describe your IT problem in "
             "English, for example: « My VPN keeps disconnecting ».")


def est_salutation(message: str) -> bool:
    """« hello », « hi there », « good morning! » : une formule, pas un problème."""
    return bool(_SALUTATION.match(message.strip())) and len(message.split()) <= 4


QUESTIONS_PRECISION = {
    "reseau": "Is it the Wi-Fi, the VPN or the network cable? Do your colleagues have the "
              "same problem?",
    "materiel": "Which device is it (laptop, printer, screen, keyboard...) and what exactly "
                "happens?",
    "logiciel": "Which application is it, and what error message do you see?",
    "compte_acces": "Which account or application is it, and what message do you get when "
                    "you sign in?",
    "facturation": "Is it about an invoice, a payment or a refund? What amount or invoice "
                   "number is concerned?",
    "securite": "What happened exactly: a suspicious email, an antivirus alert, an unknown "
                "sign-in, a lost device?",
    "panne_service": "Which service is unavailable, and is it only you or several people?",
}
QUESTION_GENERALE = ("Could you describe the problem in more detail: which device or "
                     "application, what you see on the screen, and since when?")


@dataclass
class Tour:
    role: str  # "utilisateur" ou "agent"
    texte: str
    horodatage: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    etat: Etat = Etat.NOUVELLE
    description: list[str] = field(default_factory=list)  # messages qui décrivent l'incident
    prediction: dict[str, Any] | None = None
    articles_proposes: list[str] = field(default_factory=list)
    candidats: list[dict[str, Any]] = field(default_factory=list)
    tentatives: int = 0
    precisions: int = 0
    motif_escalade: Motif | None = None
    ticket_id: str | None = None
    historique: list[Tour] = field(default_factory=list)

    def en_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Reponse:
    conversation_id: str
    etat: Etat
    message: str
    prediction: dict[str, Any] | None = None
    article: dict[str, Any] | None = None
    tentative: int = 0
    actions: list[str] = field(default_factory=list)
    brouillon_ticket: dict[str, Any] | None = None
    ticket: dict[str, Any] | None = None


class Moteur:
    def __init__(self, modele: Modele, tickets: Tickets | None = None) -> None:
        self.modele = modele
        self.tickets = tickets

    # -- point d'entrée -------------------------------------------------------------
    def repondre(self, conv: Conversation, message: str | None = None,
                 action: Action | None = None) -> Reponse:
        if message:
            conv.historique.append(Tour("utilisateur", message))
            if action is None and conv.etat in {Etat.SOLUTION_PROPOSEE, Etat.ATTENTE_PRECISION,
                                                Etat.ESCALADE_PROPOSEE}:
                action = lire_reponse(message)
                if conv.etat == Etat.ATTENTE_PRECISION and action != Action.TECHNICIEN:
                    action = None  # en attente de précision, le message est une précision
        if action is None and not message:
            raise ValueError("il faut un message ou une action")
        rep = self._router(conv, message, action)
        conv.etat = rep.etat
        conv.historique.append(Tour("agent", rep.message))
        return rep

    def _router(self, conv: Conversation, message: str | None, action: Action | None
                ) -> Reponse:
        if action == Action.CONFIRMER:
            return self._creer_ticket(conv)
        if action == Action.TECHNICIEN and conv.etat == Etat.TICKET_CREE:
            return self._creer_ticket(conv)  # le ticket existe déjà : on le rappelle
        if action == Action.TECHNICIEN and conv.description:
            return self._escalader(conv, Motif.DEMANDE)
        if conv.etat == Etat.ESCALADE_PROPOSEE and action == Action.RESOLU:
            # « yes / ok » à « Shall I create the ticket? » : la création se confirme par
            # l'action dédiée (bouton), pour ne jamais créer un ticket par erreur.
            return Reponse(conv.id, Etat.ESCALADE_PROPOSEE,
                           "Please confirm with the « Create ticket » button, or cancel.",
                           prediction=conv.prediction, tentative=conv.tentatives,
                           actions=self._actions(Etat.ESCALADE_PROPOSEE),
                           brouillon_ticket=brouillon(conv))
        if action == Action.ANNULER or (conv.etat == Etat.ESCALADE_PROPOSEE
                                        and action == Action.NON_RESOLU):
            return Reponse(conv.id, Etat.FERMEE, "No problem, no ticket was created. Write to "
                                                  "me again if the problem comes back.")
        if conv.etat == Etat.SOLUTION_PROPOSEE and action == Action.RESOLU:
            return Reponse(conv.id, Etat.RESOLUE, "Great, I'm glad it's solved. No ticket was "
                                                  "created. Have a nice day!",
                           prediction=conv.prediction, tentative=conv.tentatives)
        if conv.etat == Etat.SOLUTION_PROPOSEE and action == Action.NON_RESOLU:
            return self._essai_suivant(conv)
        if message and est_salutation(message) and conv.etat not in {
                Etat.SOLUTION_PROPOSEE, Etat.ESCALADE_PROPOSEE}:
            # une formule de politesse ne décrit pas un problème : on accueille, sans
            # consommer la question de précision
            etat = Etat.ATTENTE_PRECISION if conv.description else Etat.NOUVELLE
            return Reponse(conv.id, etat, ACCUEIL, actions=self._actions(etat))
        if conv.etat == Etat.ATTENTE_PRECISION and message:
            conv.description.append(message)
            return self._analyser(conv)
        if message:  # nouvel incident (ou suite d'une conversation terminée)
            self._reinitialiser(conv)
            conv.description.append(message)
            return self._analyser(conv)
        return Reponse(conv.id, conv.etat, "Please describe your IT problem.",
                       actions=self._actions(conv.etat))

    # -- étapes -----------------------------------------------------------------------
    def _analyser(self, conv: Conversation) -> Reponse:
        p = self.modele.predire(" ".join(conv.description))
        if p.raison == "incomprehensible":
            # charabia : on l'oublie et on redemande, sans consommer la précision
            conv.description.pop()
            etat = Etat.ATTENTE_PRECISION if conv.description else Etat.NOUVELLE
            return Reponse(conv.id, etat, INCOMPRIS, actions=self._actions(etat))
        conv.prediction = _resume(p)
        conv.candidats = p.articles
        if p.categorie == HORS_SUJET:
            return Reponse(conv.id, Etat.HORS_SUJET,
                           "Sorry, I can only help with IT problems (network, devices, "
                           "software, accounts, security, billing, outages).",
                           prediction=conv.prediction)
        premier = p.articles[0] if p.articles else None
        motif = motif_immediat(p.categorie, p.critique, premier)  # règles R1 et R2
        if motif is not None:
            return self._escalader(conv, motif, article=premier)
        if p.categorie == INDETERMINE or not p.articles:
            if conv.precisions < MAX_PRECISIONS:
                conv.precisions += 1
                question = QUESTIONS_PRECISION.get(p.categorie_probable, QUESTION_GENERALE)
                if not p.articles:  # message vide de sens : question générale
                    question = QUESTION_GENERALE
                return Reponse(conv.id, Etat.ATTENTE_PRECISION, question,
                               prediction=conv.prediction, actions=self._actions(
                                   Etat.ATTENTE_PRECISION))
            return self._escalader(conv, Motif.INDETERMINE)
        return self._proposer(conv, p.articles[0])

    def _proposer(self, conv: Conversation, article: dict[str, Any]) -> Reponse:
        conv.tentatives += 1
        conv.articles_proposes.append(article["id"])
        intro = ("Let's try this" if conv.tentatives == 1
                 else "Sorry it didn't work. Let's try another solution")
        texte = f"{intro} ({article['id']}, {article['titre']}):\n" + _etapes(article)
        texte += "\n\nDid this solve your problem?"
        return Reponse(conv.id, Etat.SOLUTION_PROPOSEE, texte, prediction=conv.prediction,
                       article=article, tentative=conv.tentatives,
                       actions=self._actions(Etat.SOLUTION_PROPOSEE))

    def _essai_suivant(self, conv: Conversation) -> Reponse:
        suivant = next((a for a in conv.candidats if a["id"] not in conv.articles_proposes),
                       None)
        if apres_echec(conv.tentatives, suivant is not None) or suivant is None:  # règle R3
            return self._escalader(conv, Motif.ECHECS)
        return self._proposer(conv, suivant)

    def _creer_ticket(self, conv: Conversation) -> Reponse:
        if conv.etat not in {Etat.ESCALADE_PROPOSEE, Etat.TICKET_CREE}:
            return Reponse(conv.id, conv.etat, "There is no ticket to confirm yet. Please "
                                               "describe your IT problem first.",
                           prediction=conv.prediction, actions=self._actions(conv.etat))
        if self.tickets is None:
            raise RuntimeError("aucun stockage de tickets configuré")
        t = self.tickets.creer(brouillon(conv))
        conv.ticket_id = t.id
        texte = (f"Ticket {t.id} is created for the {t.groupe} team (priority {t.priorite}). "
                 f"A technician will contact you within {t.delai}. Keep this number to "
                 "follow your ticket in the « Track a ticket » tab.")
        return Reponse(conv.id, Etat.TICKET_CREE, texte, prediction=conv.prediction,
                       tentative=conv.tentatives, ticket=t.en_dict())

    def _escalader(self, conv: Conversation, motif: Motif,
                   article: dict[str, Any] | None = None) -> Reponse:
        conv.motif_escalade = motif
        if article is not None and article["id"] not in conv.articles_proposes:
            conv.articles_proposes.append(article["id"])
        textes = {
            Motif.CRITIQUE: "This looks critical, so I'm sending it to a technician right "
                            "away. Meanwhile, please do this now:\n",
            Motif.ARTICLE: "A technician has to handle this request. To speed it up, please "
                           "prepare the following:\n",
            Motif.ECHECS: "The solutions did not fix the problem. I can open a ticket for a "
                          "technician with everything we tried.",
            Motif.DEMANDE: "Sure, I can open a ticket for a technician.",
            Motif.INDETERMINE: "I'm not sure which team should handle this. I can open a "
                               "ticket so that a level-1 technician sorts it out.",
        }
        texte = textes[motif] + (_etapes(article) if article else "")
        texte += "\n\nShall I create the ticket below?"
        return Reponse(conv.id, Etat.ESCALADE_PROPOSEE, texte, prediction=conv.prediction,
                       article=article, tentative=conv.tentatives,
                       actions=self._actions(Etat.ESCALADE_PROPOSEE),
                       brouillon_ticket=brouillon(conv))

    # -- outils -----------------------------------------------------------------------
    @staticmethod
    def _reinitialiser(conv: Conversation) -> None:
        conv.description, conv.articles_proposes, conv.candidats = [], [], []
        conv.prediction, conv.motif_escalade, conv.ticket_id = None, None, None
        conv.tentatives = conv.precisions = 0

    @staticmethod
    def _actions(etat: Etat) -> list[str]:
        """Boutons proposés à l'interface pour cet état."""
        actions: dict[Etat, list[str]] = {
            Etat.SOLUTION_PROPOSEE: [Action.RESOLU, Action.NON_RESOLU, Action.TECHNICIEN],
            Etat.ATTENTE_PRECISION: [Action.TECHNICIEN],
            Etat.ESCALADE_PROPOSEE: [Action.CONFIRMER, Action.ANNULER],
        }
        return actions.get(etat, [])


def _resume(p: Prediction) -> dict[str, Any]:
    return {"categorie": p.categorie, "categorie_probable": p.categorie_probable,
            "confiance": p.confiance, "priorite": p.priorite, "critique": p.critique}


def _etapes(article: dict[str, Any]) -> str:
    lignes = [f"{i}. {e}" for i, e in enumerate(article.get("etapes", []), 1)]
    if article.get("escalade_si"):
        lignes.append(f"(A technician is needed if: {article['escalade_si']})")
    return "\n".join(lignes)


def brouillon(conv: Conversation) -> dict[str, Any]:
    """Ticket pré-rempli, créé seulement après confirmation de l'employé (T6)."""
    p = conv.prediction or {}
    categorie = p.get("categorie")
    if categorie in (None, INDETERMINE, HORS_SUJET):
        categorie = INDETERMINE
    critique = bool(p.get("critique"))
    prio = priorite_ticket(p.get("priorite"), critique, conv.motif_escalade)
    return {
        "conversation_id": conv.id,
        "categorie": categorie,
        "categorie_probable": p.get("categorie_probable"),
        "priorite": prio,
        "critique": critique,
        "groupe": groupe(categorie),
        "delai": delai(prio),
        "motif": conv.motif_escalade.value if conv.motif_escalade else None,
        "description": " ".join(conv.description),
        "articles_essayes": list(conv.articles_proposes),
        "tentatives": conv.tentatives,
    }
