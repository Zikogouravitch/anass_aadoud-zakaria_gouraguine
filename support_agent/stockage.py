"""Conversations en mémoire, avec un journal JSON Lines dans tickets/ (hors Git)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from support_agent.config import TICKETS
from support_agent.conversation import Conversation


class Conversations:
    def __init__(self, journal: Path | None = TICKETS / "conversations.jsonl") -> None:
        self._donnees: dict[str, Conversation] = {}
        self._verrou = threading.Lock()
        self.journal = journal

    def nouvelle(self) -> Conversation:
        conv = Conversation()
        with self._verrou:
            self._donnees[conv.id] = conv
        return conv

    def obtenir(self, ident: str) -> Conversation | None:
        with self._verrou:
            return self._donnees.get(ident)

    def enregistrer(self, conv: Conversation) -> None:
        """Ajoute l'état courant au journal (une ligne par tour : rejouable et auditable)."""
        if self.journal is None:
            return
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        with self._verrou, self.journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(conv.en_dict(), ensure_ascii=False) + "\n")

    def __len__(self) -> int:
        return len(self._donnees)
