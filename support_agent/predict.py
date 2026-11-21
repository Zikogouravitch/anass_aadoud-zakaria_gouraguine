"""Prototype en ligne de commande : incident -> catégorie -> article.

    python -m support_agent.predict "My VPN keeps disconnecting"
    python -m support_agent.predict --json "The printer is offline"
"""

from __future__ import annotations

import argparse
import json

from support_agent.config import HORS_SUJET, INDETERMINE, get_settings
from support_agent.modele import ModeleSupport, Prediction


def afficher(p: Prediction) -> str:
    lignes = [f"Message    : {p.texte}"]
    if p.categorie == HORS_SUJET:
        lignes.append("Réponse    : hors sujet. Je traite seulement les incidents informatiques "
                      "(réseau, matériel, logiciels, comptes, sécurité, facturation, pannes).")
        return "\n".join(lignes)
    if p.categorie == INDETERMINE:
        lignes.append(f"Catégorie  : INDETERMINE (piste : {p.categorie_probable}, "
                      f"confiance {p.confiance:.2f}) -> tri par un technicien N1")
    else:
        lignes.append(f"Catégorie  : {p.categorie} (confiance {p.confiance:.2f})")
    lignes.append(f"Priorité   : {p.priorite}" + ("  ·  CAS CRITIQUE : escalade immédiate"
                                                  if p.critique else ""))
    if p.articles:
        a = p.articles[0]
        lignes.append(f"Article    : {a['id']} — {a['titre']} (score {a['score']:.2f})")
        lignes += [f"  {i}. {e}" for i, e in enumerate(a["etapes"], 1)]
        lignes.append(f"  Escalade si : {a['escalade_si']}")
        autres = ", ".join(f"{x['id']} ({x['score']:.2f})" for x in p.articles[1:])
        if autres:
            lignes.append(f"Autres     : {autres}")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> None:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("texte", nargs="+", help="description de l'incident (anglais)")
    parseur.add_argument("--json", action="store_true")
    args = parseur.parse_args(argv)
    modele = ModeleSupport.charger()
    modele.hyper = type(modele.hyper)(**{**modele.hyper.__dict__,
                                         "seuil": get_settings().seuil_abstention})
    p = modele.predire(" ".join(args.texte))
    print(json.dumps(p.en_dict(), indent=2, ensure_ascii=False) if args.json else afficher(p))


if __name__ == "__main__":  # pragma: no cover
    main()
