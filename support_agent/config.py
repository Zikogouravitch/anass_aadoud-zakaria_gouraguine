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
HORS_SUJET = "hors_sujet"
# Étiquettes apprises par le modèle : les 7 catégories IT + le hors sujet (refus poli)
ETIQUETTES: tuple[str, ...] = (*CATEGORIES, HORS_SUJET)
PRIORITES: tuple[str, ...] = ("low", "medium", "high")
INDETERMINE = "INDETERMINE"

RAW = DATA / "raw"  # téléchargements (hors Git)
PROCESSED = DATA / "processed"  # jeu d'entraînement construit (hors Git)
EVAL = DATA / "eval"  # jeux d'évaluation écrits à la main (versionnés)


class Settings(BaseSettings):
    """Valeurs lues dans l'environnement ou dans le fichier .env."""

    model_config = SettingsConfigDict(env_file=RACINE / ".env", extra="ignore")

    api_key: str = ""
    api_url: str = "http://localhost:8000"
    seuil_abstention: float = 0.50
    ollama_active: bool = False
    ollama_url: str = "http://localhost:11434"


def get_settings() -> Settings:
    return Settings()
