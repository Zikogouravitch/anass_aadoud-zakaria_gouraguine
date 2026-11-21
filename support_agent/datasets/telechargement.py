"""Téléchargement avec cache local dans data/raw/ (jamais versionné)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from support_agent.config import RAW

HF = "https://huggingface.co"
USER_AGENT = "support-agent-dataset-builder/0.1 (student project)"


def telecharger(url: str, destination: Path, timeout: float = 600) -> Path:
    """Télécharge `url` vers `destination` sauf si le fichier est déjà là."""
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    headers = {"User-Agent": USER_AGENT}
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for bloc in r.iter_bytes():
                f.write(bloc)
    tmp.replace(destination)
    return destination


def fichier_hf(depot: str, fichier: str, dossier: str) -> Path:
    """Un fichier d'un dépôt de données Hugging Face, mis en cache dans data/raw/<dossier>/."""
    nom = Path(fichier).name
    return telecharger(f"{HF}/datasets/{depot}/resolve/main/{fichier}", RAW / dossier / nom)


def json_en_cache(url: str, params: dict[str, Any], destination: Path) -> Any:
    """Appel d'API JSON mis en cache (évite de consommer le quota à chaque construction)."""
    if destination.exists():
        return json.loads(destination.read_text(encoding="utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    r = httpx.get(url, params=params, timeout=60, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    donnees = r.json()
    destination.write_text(json.dumps(donnees), encoding="utf-8")
    attente = donnees.get("backoff", 0) if isinstance(donnees, dict) else 0
    time.sleep(max(0.2, float(attente)))  # règle de l'API Stack Exchange
    return donnees
