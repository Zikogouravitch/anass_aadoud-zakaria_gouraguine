"""Entraîne le modèle et écrit models/support.joblib + models/metrics.json.

    python -m support_agent.train            # mesure sur 20 % tenus à part, puis modèle final
    python -m support_agent.train --rapide   # modèle final seulement (100 % des données)

Prérequis : `python -m support_agent.datasets.construire` (data/processed/entrainement.csv).
Les jeux de data/eval/ ne sont jamais utilisés ici.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from support_agent import __version__
from support_agent.config import MODELS, PROCESSED, get_settings
from support_agent.encodeur import Encodeur
from support_agent.modele import CHEMIN_MODELE, Hyper, ModeleSupport

GRAINE = 42


def vecteurs_en_cache(textes: list[str], encodeur: Encodeur, dossier: Path) -> np.ndarray:
    """Embeddings des textes d'entraînement, mis en cache (2 min évitées à chaque essai)."""
    empreinte = hashlib.sha1("\n".join(textes).encode("utf-8")).hexdigest()[:12]
    chemin = dossier / f"vecteurs_{empreinte}.npy"
    if chemin.exists():
        return np.load(chemin)
    vecteurs = encodeur.encode(textes)
    dossier.mkdir(parents=True, exist_ok=True)
    np.save(chemin, vecteurs)
    return vecteurs


def mesurer(y_vrai: Any, y_pred: Any, sources: pd.Series) -> dict[str, Any]:
    return {
        "f1_macro": round(float(f1_score(y_vrai, y_pred, average="macro")), 3),
        "exactitude": round(float(accuracy_score(y_vrai, y_pred)), 3),
        "exactitude_par_source": {
            str(s): round(float(accuracy_score(np.asarray(y_vrai)[m], np.asarray(y_pred)[m])), 3)
            for s in sorted(sources.unique()) if (m := (sources == s).to_numpy()).sum()
        },
        "par_classe": {
            k: {m: round(float(x), 3) for m, x in v.items()}
            for k, v in classification_report(y_vrai, y_pred, output_dict=True,
                                              zero_division=0).items()
            if isinstance(v, dict) and k not in {"macro avg", "weighted avg"}
        },
    }


def entrainer(
    df: pd.DataFrame, encodeur: Encodeur | None = None, rapide: bool = False,
    hyper: Hyper | None = None, chemin: Path = CHEMIN_MODELE, cache: Path = PROCESSED,
) -> dict[str, Any]:
    hyper = hyper or Hyper(seuil=get_settings().seuil_abstention)
    modele = ModeleSupport(hyper)
    enc = encodeur or modele.encodeur
    debut = time.perf_counter()
    vecteurs = vecteurs_en_cache(df["text"].astype(str).tolist(), enc, cache)
    metriques: dict[str, Any] = {
        "version": __version__, "lignes": len(df), "hyper": hyper.__dict__,
        "par_categorie": df["categorie"].value_counts().to_dict(),
    }
    if not rapide:
        i_app, i_test = train_test_split(np.arange(len(df)), test_size=0.2,
                                         stratify=df["categorie"], random_state=GRAINE)
        essai = ModeleSupport(hyper).utiliser(enc)
        essai.entrainer(df.iloc[i_app], vecteurs[i_app])
        test = df.iloc[i_test]
        proba = essai.probabilites(test["text"].astype(str).tolist(), vecteurs[i_test])
        pred = proba.idxmax(axis=1).to_numpy()
        metriques["test_20pct"] = mesurer(test["categorie"].to_numpy(), pred,
                                          test["source"].reset_index(drop=True))
        metriques["test_20pct"]["abstention"] = round(
            float((proba.max(axis=1) < hyper.seuil).mean()), 3)
    modele.utiliser(enc).entrainer(df, vecteurs)
    modele.sauver(chemin)
    metriques["duree_s"] = round(time.perf_counter() - debut, 1)
    (chemin.parent / "metrics.json").write_text(
        json.dumps(metriques, indent=2, ensure_ascii=False), encoding="utf-8")
    return metriques


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rapide", action="store_true", help="sans mesure sur 20 %% tenus à part")
    p.add_argument("--donnees", type=Path, default=PROCESSED / "entrainement.csv")
    args = p.parse_args(argv)
    if not args.donnees.exists():
        raise SystemExit(f"{args.donnees} absent : lancer `python -m support_agent.datasets."
                         "construire` d'abord")
    m = entrainer(pd.read_csv(args.donnees), rapide=args.rapide)
    resume: dict[str, Any] = {k: m[k] for k in ("lignes", "duree_s") if k in m}
    if "test_20pct" in m:
        t = m["test_20pct"]
        resume |= {"f1_macro_test": t["f1_macro"], "exactitude_test": t["exactitude"],
                   "exactitude_par_source": t["exactitude_par_source"],
                   "abstention": t["abstention"]}
    print(json.dumps(resume, indent=2, ensure_ascii=False))
    print(f"Modèle : {CHEMIN_MODELE} · métriques : {MODELS / 'metrics.json'}")


if __name__ == "__main__":  # pragma: no cover
    main()
