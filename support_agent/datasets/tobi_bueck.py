"""Tobi-Bueck/customer-support-tickets : tickets générés (CC BY-NC 4.0).

Seuls les incidents en anglais sont gardés. La catégorie est déduite de la file (`queue`)
puis des tags, dans l'ordre où ils apparaissent ; un ticket sans tag reconnu est écarté.
"""

from __future__ import annotations

import pandas as pd

from support_agent.datasets.nettoyage import nettoyer
from support_agent.datasets.telechargement import fichier_hf

DEPOT = "Tobi-Bueck/customer-support-tickets"
FICHIERS = (
    "aa_dataset-tickets-multi-lang-5-2-50-version.csv",
    "dataset-tickets-multi-lang-4-20k.csv",
)

FILES_DIRECTES = {
    "Billing and Payments": "facturation",
    "Service Outages and Maintenance": "panne_service",
}
FILES_EXCLUES = {
    "Sales and Pre-Sales", "Human Resources", "General Inquiry", "Returns and Exchanges",
}
TAGS: dict[str, str] = {
    **dict.fromkeys(["Security", "Virus", "Data Breach", "Vulnerability", "Malware", "Phishing",
                     "Breach", "Cybersecurity", "Fraud"], "securite"),
    **dict.fromkeys(["Outage", "Disruption", "Downtime", "Service Outage"], "panne_service"),
    **dict.fromkeys(["Account", "Login", "Authentication", "Access", "Password",
                     "Access Control"], "compte_acces"),
    **dict.fromkeys(["Billing", "Payment", "Refund", "Invoice", "Subscription"], "facturation"),
    **dict.fromkeys(["Network", "Connectivity", "VPN", "Wi-Fi", "Networking"], "reseau"),
    **dict.fromkeys(["Hardware", "Printer", "Device", "Peripheral"], "materiel"),
    **dict.fromkeys(["Software", "Bug", "Crash", "Software Update", "Update",
                     "Compatibility", "Installation"], "logiciel"),
}
TYPES_GARDES = {"Incident", "Problem"}


def categorie(queue: str, tags: list[str]) -> str | None:
    if queue in FILES_EXCLUES:
        return None
    if any(TAGS.get(t) == "securite" for t in tags):  # la sécurité passe avant la file
        return "securite"
    if queue in FILES_DIRECTES:
        return FILES_DIRECTES[queue]
    for t in tags:
        if t in TAGS:
            return TAGS[t]
    return None


def preparer(brut: pd.DataFrame) -> pd.DataFrame:
    """Brut Tobi-Bueck -> colonnes text, categorie, priorite, source."""
    df = brut[(brut["language"] == "en") & (brut["type"].isin(TYPES_GARDES))].copy()
    colonnes_tags = [c for c in df.columns if c.startswith("tag_")]
    tags = df[colonnes_tags].apply(lambda r: [t for t in r if isinstance(t, str)], axis=1)
    df["categorie"] = [categorie(q, t) for q, t in zip(df["queue"], tags, strict=True)]
    df = df[df["categorie"].notna()]
    texte = df["subject"].fillna("") + ". " + df["body"].fillna("")
    return pd.DataFrame({
        "text": texte.map(nettoyer).str.strip(". "),
        "categorie": df["categorie"],
        "priorite": df["priority"].where(df["priority"].isin(["low", "medium", "high"])),
        "source": "tobi_bueck",
    })


def charger() -> pd.DataFrame:
    brut = pd.concat(
        [pd.read_csv(fichier_hf(DEPOT, f, "tobi_bueck")) for f in FICHIERS], ignore_index=True
    )
    return preparer(brut)
