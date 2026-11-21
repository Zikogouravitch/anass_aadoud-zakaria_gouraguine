"""Super User (Stack Exchange) : vraies questions d'utilisateurs, licence CC BY-SA 4.0.

Deux accès :
- le dump `marianna13/superuser` sur Hugging Face (28 506 questions, titres + tags) ;
- l'API publique Stack Exchange pour renforcer les catégories rares (sécurité, comptes).

La catégorie vient des tags ; seuls les titres qui décrivent un incident sont gardés
(« not working », « can't », « keeps disconnecting », ...).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from support_agent.config import RAW
from support_agent.datasets.nettoyage import est_anglais, nettoyer
from support_agent.datasets.telechargement import fichier_hf, json_en_cache

DEPOT_DUMP = "marianna13/superuser"
FICHIER_DUMP = "part-00000-65566ee6-33bd-4ad6-8a8f-285e142dc663-c000.snappy.parquet"
API = "https://api.stackexchange.com/2.3/questions"

# Ordre = priorité quand plusieurs catégories correspondent.
TAGS: dict[str, set[str]] = {
    "securite": {"phishing", "malware", "virus", "antivirus", "ransomware", "spyware",
                 "malware-removal", "trojan", "hacking", "rootkit", "adware", "email-spam",
                 "keylogger", "scam", "account-security", "compromise", "spoofing"},
    "compte_acces": {"password", "passwords", "login", "user-accounts", "permissions",
                     "authentication", "active-directory", "uac", "two-factor-authentication",
                     "password-recovery", "microsoft-account", "logon", "single-sign-on",
                     "access-control", "lockout"},
    "reseau": {"networking", "wireless-networking", "wifi", "router", "vpn", "dns", "ethernet",
               "internet-connection", "proxy", "network-adapter", "wireless-router", "internet",
               "network-shares", "lan", "dhcp", "ip-address", "openvpn", "cisco-vpn-client"},
    "materiel": {"printer", "printing", "hard-drive", "display", "monitor", "keyboard", "mouse",
                 "laptop", "usb", "battery", "hardware-failure", "cpu", "graphics-card",
                 "power-supply", "webcam", "overheating", "fan", "ssd", "motherboard",
                 "touchpad", "headphones", "speakers", "scanner", "ram", "multiple-monitors",
                 "bsod", "microphone", "docking-station", "charger"},
    "logiciel": {"microsoft-excel", "microsoft-word", "microsoft-outlook", "google-chrome",
                 "firefox", "windows-update", "crash", "installation", "microsoft-office",
                 "microsoft-teams", "skype", "adobe-reader", "microsoft-powerpoint", "office365",
                 "onedrive", "windows-explorer", "microsoft-edge", "zoom", "outlook",
                 "microsoft-outlook-2010", "microsoft-outlook-2013", "microsoft-outlook-2016",
                 "microsoft-excel-2010", "microsoft-excel-2013", "microsoft-excel-2016"},
}
# Catégories qui l'emportent même si un autre tag correspond.
PRIORITAIRES = ("securite", "compte_acces")

INCIDENT = re.compile(
    r"not working|doesn'?t work|does not|won'?t|can'?t|cannot|unable|error|fail|crash|freez"
    r"|slow|keeps?\b|stopp|stuck|broken|lost|missing|no (?:internet|sound|signal|display|wifi)"
    r"|disconnect|drops?\b|hang|problem|issue|not (?:showing|responding|detected|recogni"
    r"|connecting|loading|opening|printing|booting|turning|syncing|working)|blue screen"
    r"|infected|hacked|compromised|locked|forgot|denied|expired|why (?:is|does|did|won|can)",
    re.I,
)
# Un mot du domaine (virus, phishing...) ne suffit que si la phrase raconte un vécu.
SUJET = re.compile(r"phishing|virus|malware|ransomware|scam|suspicious|trojan|spyware", re.I)
VECU = re.compile(r"\b(?:my|i|i'?ve|i'?m|i got|someone|me|our)\b", re.I)


def decrit_incident(titre: str) -> bool:
    return bool(INCIDENT.search(titre) or (SUJET.search(titre) and VECU.search(titre)))

# Requêtes d'API pour les catégories rares : (site, tag)
TAGS_API: tuple[tuple[str, str], ...] = (
    ("superuser", "phishing"), ("superuser", "malware"), ("superuser", "virus"),
    ("superuser", "ransomware"), ("superuser", "malware-removal"), ("superuser", "hacking"),
    ("security", "phishing"), ("security", "account-security"), ("security", "malware"),
    ("security", "ransomware"), ("security", "compromise"), ("security", "scam"),
    ("superuser", "password"), ("superuser", "login"), ("superuser", "user-accounts"),
    ("superuser", "two-factor-authentication"), ("superuser", "microsoft-account"),
    ("superuser", "permissions"), ("superuser", "printer"), ("superuser", "vpn"),
)
PAGES_API = 3


def categorie(tags: Iterable[str]) -> str | None:
    tags = set(tags)
    for c in PRIORITAIRES:
        if tags & TAGS[c]:
            return c
    trouvees = [c for c, s in TAGS.items() if tags & s]
    return trouvees[0] if len(trouvees) == 1 else None  # ambigu -> écarté


def preparer(titres: pd.Series, tags: pd.Series, source: str) -> pd.DataFrame:
    df = pd.DataFrame({"text": titres.map(nettoyer), "tags": tags})
    df["categorie"] = df["tags"].map(categorie)
    garde = (
        df["categorie"].notna()
        & df["text"].map(decrit_incident)
        & df["text"].map(est_anglais)
        & df["text"].str.count(r"\S+").between(3, 40)
    )
    df = df[garde]
    return pd.DataFrame({
        "text": df["text"], "categorie": df["categorie"], "priorite": None, "source": source,
    })


def charger_dump() -> pd.DataFrame:
    brut = pd.read_parquet(fichier_hf(DEPOT_DUMP, FICHIER_DUMP, "superuser"))
    tags = brut["CATEGORIES"].fillna("").str.split(";")
    return preparer(brut["TOPIC_TITLE"], tags, "superuser")


def charger_api() -> pd.DataFrame:
    titres: list[str] = []
    tags: list[list[str]] = []
    for site, tag in TAGS_API:
        for page in range(1, PAGES_API + 1):
            params = {"site": site, "tagged": tag, "pagesize": 100, "page": page,
                      "sort": "votes", "order": "desc"}
            rep = json_en_cache(API, params, RAW / "stackexchange" / f"{site}_{tag}_{page}.json")
            for q in rep.get("items", []):
                titres.append(q["title"])
                tags.append(q.get("tags", []))
            if not rep.get("has_more"):
                break
    return preparer(pd.Series(titres, dtype=str), pd.Series(tags, dtype=object), "stackexchange")


def charger() -> pd.DataFrame:
    return pd.concat([charger_dump(), charger_api()], ignore_index=True)
