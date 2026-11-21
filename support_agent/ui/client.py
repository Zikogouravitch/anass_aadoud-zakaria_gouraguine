"""Client HTTP de l'API, utilisé par l'interface."""

from __future__ import annotations

from typing import Any

import httpx

from support_agent.config import get_settings


class ErreurAPI(RuntimeError):
    """L'API est injoignable ou a renvoyé une erreur ; le message est lisible tel quel."""


class ClientAPI:
    def __init__(self, url: str | None = None, cle: str | None = None,
                 transport: httpx.BaseTransport | None = None, timeout: float = 30) -> None:
        reglages = get_settings()
        entetes = {"X-API-Key": cle if cle is not None else reglages.api_key}
        self._http = httpx.Client(base_url=url or reglages.api_url, headers=entetes,
                                  timeout=timeout, transport=transport)

    def _appel(self, methode: str, chemin: str, **kw: Any) -> dict[str, Any]:
        try:
            r = self._http.request(methode, chemin, **kw)
        except httpx.HTTPError as e:
            raise ErreurAPI(f"API injoignable ({self._http.base_url}) : lancez "
                            "`uvicorn support_agent.api.main:app`") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ErreurAPI(f"Erreur {r.status_code} : {detail}")
        donnees: dict[str, Any] = r.json()
        return donnees

    def sante(self) -> dict[str, Any]:
        return self._appel("GET", "/health")

    def ticket(self, ident: str) -> dict[str, Any]:
        return self._appel("GET", f"/tickets/{ident}")

    def chat(self, message: str | None = None, conversation_id: str | None = None,
             action: str | None = None) -> dict[str, Any]:
        corps = {"message": message, "conversation_id": conversation_id, "action": action}
        return self._appel("POST", "/chat", json={k: v for k, v in corps.items() if v})
