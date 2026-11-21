"""CLINC150 (clinc/clinc_oos, CC BY 3.0) : vraies requêtes collectées par crowdsourcing.

Sert d'exemples `hors_sujet` (météo, cuisine, voyages, ...). Les intentions proches du
support (carte bloquée, facture, mot de passe, appareil perdu) et les formules de
conversation (bonjour, merci, oui, non) sont écartées : le chat les gère autrement.
"""

from __future__ import annotations

import pandas as pd

from support_agent.config import HORS_SUJET, RAW
from support_agent.datasets.nettoyage import nettoyer
from support_agent.datasets.telechargement import telecharger

URL = "https://huggingface.co/api/datasets/clinc/clinc_oos/parquet/plus/train/0.parquet"
URL_INFO = "https://datasets-server.huggingface.co/info?dataset=clinc/clinc_oos&config=plus"

EXCLUES = {
    # proches de la facturation, des comptes ou du matériel
    "account_blocked", "report_lost_card", "freeze_account", "bill_balance", "card_declined",
    "bill_due", "report_fraud", "damaged_card", "reset_settings", "pin_change",
    "replacement_card_duration", "new_card", "pay_bill", "sync_device", "find_phone",
    "transactions", "expiration_date", "change_user_name", "user_name", "credit_limit_change",
    # formules de conversation
    "greeting", "goodbye", "thank_you", "yes", "no", "maybe", "repeat", "cancel",
    "what_can_i_ask_you", "are_you_a_bot",
}


def noms_intentions() -> list[str]:
    import json

    chemin = telecharger(URL_INFO, RAW / "clinc" / "info.json")
    info = json.loads(chemin.read_text(encoding="utf-8"))
    return list(info["dataset_info"]["features"]["intent"]["names"])


def preparer(brut: pd.DataFrame, noms: list[str], n: int, graine: int = 42) -> pd.DataFrame:
    df = brut.assign(nom=brut["intent"].map(lambda i: noms[i]))
    df = df[~df["nom"].isin(EXCLUES)]
    # échantillon équilibré entre intentions pour couvrir beaucoup de sujets
    par_intention = max(1, n // df["nom"].nunique())
    df = df.sample(frac=1, random_state=graine).groupby("nom").head(par_intention)
    return pd.DataFrame({
        "text": df["text"].map(nettoyer).str.capitalize(),
        "categorie": HORS_SUJET, "priorite": None, "source": "clinc150",
    })


def charger(n: int = 1500) -> pd.DataFrame:
    brut = pd.read_parquet(telecharger(URL, RAW / "clinc" / "train.parquet"))
    return preparer(brut, noms_intentions(), n)
