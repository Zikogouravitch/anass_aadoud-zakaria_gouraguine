"""Construit data/processed/entrainement.csv à partir des trois sources.

    python -m support_agent.datasets.construire

Étapes : téléchargement (cache data/raw/), étiquetage, nettoyage, retrait des doublons,
plafond par source et par catégorie (équilibre), retrait de tout texte trop proche
d'un jeu d'évaluation (anti-fuite), écriture du CSV et d'un résumé JSON.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable

import pandas as pd

from support_agent.config import EVAL, PROCESSED
from support_agent.datasets import clinc, superuser, tobi_bueck
from support_agent.datasets.nettoyage import cle, jaccard, mots

SEUIL_FUITE = 0.6  # similarité (Jaccard sur les mots) au-delà de laquelle on retire
MAX_MOTS = 150  # les tickets Tobi-Bueck très longs sont coupés
PLAFOND_TOBI = 1200  # par catégorie : évite que les longs tickets générés dominent
GRAINE = 42


def couper(texte: str, n: int = MAX_MOTS) -> str:
    morceaux = texte.split()
    return texte if len(morceaux) <= n else " ".join(morceaux[:n])


def dedoublonner(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les doublons ; un texte présent avec deux catégories différentes est écarté."""
    df = df.assign(_cle=df["text"].map(cle))
    df = df[df["_cle"].str.len() > 0]
    nb_cat = df.groupby("_cle")["categorie"].transform("nunique")
    df = df[nb_cat == 1].drop_duplicates("_cle")
    return df.drop(columns="_cle")


def plafonner(df: pd.DataFrame, source: str, plafond: int) -> pd.DataFrame:
    a_part = df[df["source"] == source]
    reste = df[df["source"] != source]
    a_part = a_part.sample(frac=1, random_state=GRAINE).groupby("categorie").head(plafond)
    return pd.concat([reste, a_part], ignore_index=True)


def retirer_fuites(df: pd.DataFrame, textes_eval: Iterable[str]) -> tuple[pd.DataFrame, int]:
    """Retire les textes identiques ou très proches d'un texte d'évaluation."""
    eval_mots = [mots(t) for t in textes_eval]
    eval_cles = {cle(t) for t in textes_eval}

    def fuite(texte: str) -> bool:
        if cle(texte) in eval_cles:
            return True
        m = mots(texte)
        return len(m) <= 40 and any(jaccard(m, e) >= SEUIL_FUITE for e in eval_mots)

    masque = df["text"].map(fuite)
    return df[~masque].reset_index(drop=True), int(masque.sum())


def textes_evaluation() -> list[str]:
    textes: list[str] = []
    for f in sorted(EVAL.glob("*.csv")):
        textes += pd.read_csv(f)["text"].astype(str).tolist()
    return textes


def construire(n_hors_sujet: int = 1500) -> dict[str, object]:
    sources = {
        "tobi_bueck": tobi_bueck.charger(),
        "superuser+stackexchange": superuser.charger(),
        "clinc150": clinc.charger(n_hors_sujet),
    }
    brut = {k: len(v) for k, v in sources.items()}
    df = pd.concat(sources.values(), ignore_index=True)
    df["text"] = df["text"].map(couper)
    df = dedoublonner(df)
    apres_doublons = len(df)
    df = plafonner(df, "tobi_bueck", PLAFOND_TOBI)
    df, fuites = retirer_fuites(df, textes_evaluation())
    df = df.sample(frac=1, random_state=GRAINE).reset_index(drop=True)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / "entrainement.csv", index=False)
    resume: dict[str, object] = {
        "lignes_par_source_avant_fusion": brut,
        "apres_doublons": apres_doublons,
        "retires_anti_fuite": fuites,
        "lignes_finales": len(df),
        "par_categorie": df["categorie"].value_counts().to_dict(),
        "par_source": df["source"].value_counts().to_dict(),
        "par_source_et_categorie": {
            s: g["categorie"].value_counts().to_dict() for s, g in df.groupby("source")
        },
        "mots_moyens_par_source": df.assign(n=df["text"].str.count(r"\S+"))
        .groupby("source")["n"].mean().round(1).to_dict(),
    }
    (PROCESSED / "resume.json").write_text(
        json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return resume


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hors-sujet", type=int, default=1500, help="exemples CLINC150 à garder")
    args = p.parse_args(argv)
    print(json.dumps(construire(args.hors_sujet), indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    main()
