"""Recalcule les chiffres de la fiche de suivi (rubrique 5, « Description du jeu de données »).

    python -m support_agent.decrire            # tableaux Markdown dans le terminal
    python -m support_agent.decrire --json     # même contenu en JSON
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from support_agent.config import EVAL, PROCESSED, SAMPLE
from support_agent.data import JEUX_EVAL, charger_jeu_eval


def _profil(df: pd.DataFrame, cible: str) -> dict[str, Any]:
    longueur = df["text"].astype(str).str.count(r"\S+")
    return {
        "lignes": len(df),
        "colonnes": len(df.columns),
        "mots_moyens": round(float(longueur.mean()), 1),
        "mots_median": float(longueur.median()),
        "repartition": df[cible].value_counts().to_dict(),
        "manquants_pct": {c: round(float(v) * 100, 1)
                          for c, v in df.isna().mean().items() if v > 0},
        "doublons_texte": int(df["text"].duplicated().sum()),
    }


def decrire(entrainement: Path = PROCESSED / "entrainement.csv") -> dict[str, Any]:
    res: dict[str, Any] = {}
    res["echantillon_tobi_bueck"] = _profil(
        pd.read_csv(SAMPLE / "tobi_bueck_extrait.csv"), "categorie")
    base = pd.read_csv(SAMPLE / "base_connaissances.csv")
    res["base_connaissances"] = {
        "articles": len(base),
        "par_categorie": base["categorie"].value_counts().to_dict(),
        "source_manquante": int(base["source"].isna().sum()),
    }
    for nom in JEUX_EVAL:
        if (EVAL / f"jeu_{nom}.csv").exists():
            df = charger_jeu_eval(nom)
            p = _profil(df, "attendu")
            p["critiques"] = int(df["critique"].sum())
            p["difficiles"] = int((df["difficulte"] != "").sum())
            res[f"jeu_{nom}"] = p
    if entrainement.exists():
        df = pd.read_csv(entrainement)
        p = _profil(df, "categorie")
        p["par_source"] = df["source"].value_counts().to_dict()
        p["mots_moyens_par_source"] = (
            df.assign(n=df["text"].str.count(r"\S+"))
            .groupby("source")["n"].mean().round(1).to_dict()
        )
        res["entrainement"] = p
    return res


def en_markdown(res: dict[str, Any]) -> str:
    lignes = ["| Jeu | Lignes | Mots moyens | Répartition |", "| --- | --- | --- | --- |"]
    for nom, p in res.items():
        if "lignes" not in p:
            continue
        rep = ", ".join(f"`{k}` {v}" for k, v in p["repartition"].items())
        lignes.append(f"| {nom} | {p['lignes']} | {p['mots_moyens']} | {rep} |")
    b = res["base_connaissances"]
    lignes.append("")
    lignes.append(f"Base de connaissances : {b['articles']} articles, "
                  f"source manquante pour {b['source_manquante']}.")
    if "entrainement" in res:
        e = res["entrainement"]
        par_source = ", ".join(f"{k} {v} ({e['mots_moyens_par_source'][k]} mots)"
                               for k, v in e["par_source"].items())
        lignes.append(f"Entraînement par source : {par_source}.")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    res = decrire()
    print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else en_markdown(res))


if __name__ == "__main__":  # pragma: no cover
    main()
