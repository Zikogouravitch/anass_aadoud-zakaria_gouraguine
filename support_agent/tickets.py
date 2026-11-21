"""Tickets : création après confirmation, identifiant lisible, suivi.

Stockage en JSON Lines (tickets/tickets.jsonl, hors Git) : chaque ligne est l'état complet
d'un ticket ; la dernière ligne d'un identifiant fait foi (historique conservé).
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from support_agent.config import TICKETS
from support_agent.escalade import delai, groupe, priorite_ticket


class Statut(StrEnum):
    OUVERT = "ouvert"
    EN_COURS = "en_cours"
    RESOLU = "resolu"
    FERME = "ferme"


def maintenant() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Ticket:
    id: str
    conversation_id: str
    categorie: str
    categorie_probable: str | None
    priorite: str
    critique: bool
    groupe: str
    delai: str
    motif: str | None
    description: str
    articles_essayes: list[str]
    tentatives: int
    statut: Statut = Statut.OUVERT
    cree_le: str = field(default_factory=maintenant)
    maj_le: str = field(default_factory=maintenant)
    note: str = ""

    def en_dict(self) -> dict[str, Any]:
        return asdict(self)


class Tickets:
    def __init__(self, fichier: Path | None = TICKETS / "tickets.jsonl") -> None:
        self.fichier = fichier
        self._verrou = threading.Lock()
        self._donnees: dict[str, Ticket] = {}
        if fichier is not None and fichier.exists():
            for ligne in fichier.read_text(encoding="utf-8").splitlines():
                if ligne.strip():
                    d = json.loads(ligne)
                    d["statut"] = Statut(d["statut"])
                    self._donnees[d["id"]] = Ticket(**d)

    def _ecrire(self, t: Ticket) -> None:
        if self.fichier is None:
            return
        self.fichier.parent.mkdir(parents=True, exist_ok=True)
        with self.fichier.open("a", encoding="utf-8") as f:
            f.write(json.dumps(t.en_dict(), ensure_ascii=False) + "\n")

    def creer(self, brouillon: dict[str, Any]) -> Ticket:
        """Crée le ticket à partir du brouillon de la conversation (après confirmation)."""
        with self._verrou:
            existant = self.par_conversation(brouillon["conversation_id"], verrou=False)
            if existant is not None and existant.description == brouillon.get("description", ""):
                return existant  # même incident (double clic, nouvel envoi) : pas de doublon
            prio = priorite_ticket(brouillon.get("priorite"), bool(brouillon.get("critique")),
                                   brouillon.get("motif"))
            t = Ticket(
                id=f"INC-{len(self._donnees) + 1:05d}",
                conversation_id=brouillon["conversation_id"],
                categorie=brouillon["categorie"],
                categorie_probable=brouillon.get("categorie_probable"),
                priorite=prio,
                critique=bool(brouillon.get("critique")),
                groupe=groupe(brouillon["categorie"]),
                delai=delai(prio),
                motif=brouillon.get("motif"),
                description=brouillon.get("description", ""),
                articles_essayes=list(brouillon.get("articles_essayes", [])),
                tentatives=int(brouillon.get("tentatives", 0)),
            )
            self._donnees[t.id] = t
            self._ecrire(t)
            return t

    def obtenir(self, ident: str) -> Ticket | None:
        return self._donnees.get(ident.strip().upper())

    def par_conversation(self, conversation_id: str, verrou: bool = True) -> Ticket | None:
        def chercher() -> Ticket | None:
            trouves = [t for t in self._donnees.values() if t.conversation_id == conversation_id]
            return trouves[-1] if trouves else None

        if not verrou:
            return chercher()
        with self._verrou:
            return chercher()

    def changer_statut(self, ident: str, statut: Statut, note: str = "") -> Ticket | None:
        with self._verrou:
            t = self._donnees.get(ident)
            if t is None:
                return None
            t.statut, t.maj_le = statut, maintenant()
            if note:
                t.note = note
            self._ecrire(t)
            return t

    def lister(self, statut: Statut | None = None, limite: int = 100) -> list[Ticket]:
        """Tickets, cas critiques puis priorité haute en tête, les plus récents d'abord."""
        rang = {"high": 0, "medium": 1, "low": 2}
        ts = [t for t in self._donnees.values() if statut is None or t.statut == statut]
        ts.sort(key=lambda t: t.cree_le, reverse=True)
        ts.sort(key=lambda t: (not t.critique, rang.get(t.priorite, 1)))
        return ts[:limite]

    def __len__(self) -> int:
        return len(self._donnees)
