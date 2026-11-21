"""Configuration centrale : chemins du projet et variables d'environnement (.env)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
SAMPLE = DATA / "sample"
MODELS = RACINE / "models"
TICKETS = RACINE / "tickets"

CATEGORIES: tuple[str, ...] = (
    "compte_acces",
    "facturation",
    "logiciel",
    "materiel",
    "panne_service",
    "reseau",
    "securite",
)
PRIORITES: tuple[str, ...] = ("low", "medium", "high")
INDETERMINE = "INDETERMINE"


class Settings(BaseSettings):
    """Valeurs lues dans l'environnement ou dans le fichier .env."""

    model_config = SettingsConfigDict(env_file=RACINE / ".env", extra="ignore")

    api_key: str = ""
    api_url: str = "http://localhost:8000"
    seuil_abstention: float = 0.60
    ollama_active: bool = False
    ollama_url: str = "http://localhost:11434"


def get_settings() -> Settings:
    return Settings()
