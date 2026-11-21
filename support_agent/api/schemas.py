"""Contrats d'échange de l'API (validation Pydantic)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from support_agent.conversation import Action, Etat

TAILLE_MAX = 2000


def _nettoyer(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


class PredictRequete(BaseModel):
    text: str = Field(min_length=1, max_length=TAILLE_MAX,
                      examples=["My VPN keeps disconnecting every 10 minutes"])

    @field_validator("text")
    @classmethod
    def non_vide(cls, v: str) -> str:
        v = _nettoyer(v) or ""
        if not v:
            raise ValueError("le texte est vide")
        return v


class Article(BaseModel):
    id: str
    titre: str
    categorie: str
    score: float
    etapes: list[str]
    escalade_si: str


class PredictReponse(BaseModel):
    texte: str
    categorie: str
    categorie_probable: str
    confiance: float
    priorite: str
    critique: bool
    articles: list[Article]
    alternatives: list[dict[str, Any]]


class ChatRequete(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=TAILLE_MAX,
                                examples=["My VPN keeps disconnecting"])
    action: Action | None = None

    @field_validator("message")
    @classmethod
    def nettoyer(cls, v: str | None) -> str | None:
        return _nettoyer(v)

    @model_validator(mode="after")
    def message_ou_action(self) -> ChatRequete:
        if self.message is None and self.action is None:
            raise ValueError("il faut un message ou une action")
        if self.action is not None and self.conversation_id is None:
            raise ValueError("une action demande un conversation_id")
        return self


class ChatReponse(BaseModel):
    conversation_id: str
    etat: Etat
    message: str
    prediction: dict[str, Any] | None = None
    article: Article | None = None
    tentative: int = 0
    actions: list[str] = []
    brouillon_ticket: dict[str, Any] | None = None


class Sante(BaseModel):
    status: str
    modele_charge: bool
    version: str
