"""Mesure du modèle sur un jeu d'évaluation écrit à la main.

    python -m support_agent.evaluer validation              # mesure de départ (T7), répétable
    python -m support_agent.evaluer independant --final     # mesure finale (T12), UNE seule fois

Écrit models/eval_<jeu>.json : F1 macro, top-1 et top-3 des articles, abstention, cas
critiques manqués, hors sujet refusés, détail par classe et par difficulté, erreurs.

Le jeu indépendant est protégé : sa lecture demande --final et laisse une trace
(models/independant_lu.json) ; une seconde lecture est refusée sauf --relire, qui reste
inscrite dans le résultat. Ainsi on ne règle jamais le modèle sur ce jeu.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from support_agent import __version__
from support_agent.config import ETIQUETTES, EVAL, HORS_SUJET, INDETERMINE, MODELS, get_settings
from support_agent.data import charger_jeu_eval
from support_agent.modele import CHEMIN_MODELE, ModeleSupport, Prediction

TRACE_INDEPENDANT = MODELS / "independant_lu.json"


class Modele(Protocol):
    def predire(self, texte: str, k: int = 3) -> Prediction: ...


class LectureInterdite(RuntimeError):
    """Le jeu indépendant a déjà été lu, ou sa lecture n'a pas été demandée explicitement."""


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()[:12]


def verifier_acces(jeu: str, final: bool, relire: bool, trace: Path = TRACE_INDEPENDANT
                   ) -> list[dict[str, Any]]:
    """Contrôle d'accès au jeu indépendant ; renvoie l'historique des lectures."""
    if jeu != "independant":
        return []
    if not final:
        raise LectureInterdite("le jeu indépendant sert à la mesure finale (T12) : "
                               "ajouter --final, en sachant qu'il ne se lit qu'une fois")
    lectures: list[dict[str, Any]] = (json.loads(trace.read_text(encoding="utf-8"))
                                      if trace.exists() else [])
    if lectures and not relire:
        raise LectureInterdite(f"jeu indépendant déjà lu le {lectures[0]['date']} : "
                               "relecture refusée (--relire pour forcer, et elle sera tracée)")
    return lectures


def tracer_lecture(lectures: list[dict[str, Any]], resultat: dict[str, Any],
                   trace: Path = TRACE_INDEPENDANT) -> None:
    lectures.append({"date": resultat["date"], "f1_macro": resultat["f1_macro"],
                     "empreinte_jeu": resultat["empreinte_jeu"]})
    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_text(json.dumps(lectures, indent=2, ensure_ascii=False), encoding="utf-8")


def _taux(n: int, total: int) -> float | None:
    return round(n / total, 3) if total else None


def mesurer(modele: Modele, df: pd.DataFrame) -> dict[str, Any]:
    """Toutes les mesures sur un jeu (colonnes text, attendu, articles_ok, critique, difficulte)."""
    debut = time.perf_counter()
    preds: list[Prediction] = [modele.predire(t) for t in df["text"].astype(str)]
    duree_ms = (time.perf_counter() - debut) * 1000 / max(1, len(df))

    attendu = df["attendu"].to_numpy()
    probable = np.array([p.categorie_probable for p in preds])  # sans abstention
    repondu = np.array([p.categorie for p in preds])  # avec abstention (INDETERMINE)
    abstenu = repondu == INDETERMINE

    it = attendu != HORS_SUJET
    top1 = top3 = 0
    for p, ok, est_it in zip(preds, df["articles_ok"], it, strict=True):
        if not est_it:
            continue
        ids = [a["id"] for a in p.articles]
        bons = set(str(ok).split("|"))
        top1 += bool(ids) and ids[0] in bons
        top3 += bool(set(ids[:3]) & bons)

    critique = df["critique"].to_numpy() == 1
    critiques_manques = int(sum(1 for p, c in zip(preds, critique, strict=True)
                                if c and not p.critique))
    hors_sujet = attendu == HORS_SUJET
    refuses = int(sum(r == HORS_SUJET for r, h in zip(repondu, hors_sujet, strict=True) if h))
    faux_refus = int(sum(r == HORS_SUJET for r, h in zip(repondu, hors_sujet, strict=True)
                         if not h))

    etiquettes = [e for e in ETIQUETTES if e in set(attendu) | set(probable)]
    rapport = classification_report(attendu, probable, labels=etiquettes, output_dict=True,
                                    zero_division=0)
    difficulte = df["difficulte"].replace("", "simple").to_numpy()
    erreurs = [
        {"text": t, "attendu": a, "predit": p.categorie, "probable": p.categorie_probable,
         "confiance": p.confiance, "raison": p.raison,
         "article": p.articles[0]["id"] if p.articles else None}
        for t, p, a in zip(df["text"].astype(str), preds, attendu, strict=True)
        if p.categorie_probable != a
    ]
    return {
        "lignes": len(df),
        "f1_macro": round(float(f1_score(attendu, probable, average="macro")), 3),
        "exactitude": round(float((probable == attendu).mean()), 3),
        "top1": _taux(top1, int(it.sum())),
        "top3": _taux(top3, int(it.sum())),
        "abstention": round(float(abstenu.mean()), 3),
        "exactitude_reponses_donnees": _taux(int(((repondu == attendu) & ~abstenu).sum()),
                                             int((~abstenu).sum())),
        "f1_macro_avec_abstention": round(float(f1_score(attendu, repondu, average="macro",
                                                         labels=etiquettes)), 3),
        "critiques": {"total": int(critique.sum()), "manques": critiques_manques},
        "hors_sujet": {"total": int(hors_sujet.sum()), "refuses": refuses,
                       "taux_refus": _taux(refuses, int(hors_sujet.sum())),
                       "refus_a_tort": faux_refus},
        "par_classe": {e: {"precision": round(rapport[e]["precision"], 3),
                           "rappel": round(rapport[e]["recall"], 3),
                           "f1": round(rapport[e]["f1-score"], 3),
                           "effectif": int(rapport[e]["support"])} for e in etiquettes},
        "par_difficulte": {
            d: {"lignes": int((difficulte == d).sum()),
                "exactitude": round(float((probable[difficulte == d]
                                           == attendu[difficulte == d]).mean()), 3)}
            for d in sorted(set(difficulte))
        },
        "matrice_confusion": {"etiquettes": etiquettes,
                              "valeurs": confusion_matrix(attendu, probable,
                                                          labels=etiquettes).tolist()},
        "temps_moyen_ms": round(duree_ms, 1),
        "erreurs": erreurs,
    }


def evaluer(modele: Modele, jeu: str, final: bool = False, relire: bool = False,
            dossier: Path = EVAL, sortie: Path = MODELS, trace: Path = TRACE_INDEPENDANT,
            infos_modele: dict[str, Any] | None = None) -> dict[str, Any]:
    lectures = verifier_acces(jeu, final, relire, trace)
    chemin = dossier / f"jeu_{jeu}.csv"
    resultat: dict[str, Any] = {
        "jeu": jeu, "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "version": __version__, "empreinte_jeu": empreinte(chemin),
        "modele": infos_modele or {},
    }
    resultat |= mesurer(modele, charger_jeu_eval(jeu, dossier))
    if jeu == "independant":
        resultat["lecture_numero"] = len(lectures) + 1
        tracer_lecture(lectures, resultat, trace)
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / f"eval_{jeu}.json").write_text(
        json.dumps(resultat, indent=2, ensure_ascii=False), encoding="utf-8")
    return resultat


def resume(r: dict[str, Any]) -> str:
    """Tableau Markdown prêt à coller dans la fiche de suivi."""
    c, h = r["critiques"], r["hors_sujet"]
    lignes = [
        f"Mesure sur `jeu_{r['jeu']}.csv` ({r['lignes']} messages) — {r['date']}",
        "",
        "| Mesure | Valeur |", "| --- | --- |",
        f"| F1 macro | **{r['f1_macro']}** |",
        f"| Exactitude | {r['exactitude']} |",
        f"| Bon article en top-1 | **{r['top1']}** |",
        f"| Bon article en top-3 | **{r['top3']}** |",
        f"| Abstention (INDETERMINE) | {r['abstention']} |",
        f"| Exactitude des réponses données | {r['exactitude_reponses_donnees']} |",
        f"| Cas critiques manqués | {c['manques']} / {c['total']} |",
        f"| Hors sujet refusés | {h['refuses']} / {h['total']} (refus à tort : "
        f"{h['refus_a_tort']}) |",
        f"| Temps moyen par message | {r['temps_moyen_ms']} ms |",
        "", "| Classe | Précision | Rappel | F1 | Effectif |", "| --- | --- | --- | --- | --- |",
    ]
    lignes += [f"| `{e}` | {v['precision']} | {v['rappel']} | {v['f1']} | {v['effectif']} |"
               for e, v in r["par_classe"].items()]
    lignes += ["", "| Difficulté | Lignes | Exactitude |", "| --- | --- | --- |"]
    lignes += [f"| {d} | {v['lignes']} | {v['exactitude']} |"
               for d, v in r["par_difficulte"].items()]
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("jeu", choices=["validation", "independant"])
    p.add_argument("--final", action="store_true", help="autorise la lecture du jeu indépendant")
    p.add_argument("--relire", action="store_true", help="force une 2e lecture (tracée)")
    args = p.parse_args(argv)
    modele = ModeleSupport.charger()
    modele.hyper = type(modele.hyper)(**{**modele.hyper.__dict__,
                                         "seuil": get_settings().seuil_abstention})
    infos = {"fichier": str(CHEMIN_MODELE.name), "empreinte": empreinte(CHEMIN_MODELE),
             "hyper": modele.hyper.__dict__}
    modele.predire("warm up: my VPN does not connect")  # charge MiniLM hors chronomètre
    try:
        r = evaluer(modele, args.jeu, args.final, args.relire, infos_modele=infos)
    except LectureInterdite as e:
        raise SystemExit(f"Refusé : {e}") from e
    print(resume(r))
    print(f"\nRésultat complet : {MODELS / f'eval_{args.jeu}.json'}")


if __name__ == "__main__":  # pragma: no cover
    main()
