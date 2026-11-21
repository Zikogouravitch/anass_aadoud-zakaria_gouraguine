"""Rejoue les 30 conversations de data/eval/conversations.json avec le vrai modèle.

    python -m support_agent.bilan_tickets          # tableau + models/bilan_tickets.json

Critère de T6 : les 30 conversations donnent 10 tickets, tous attendus (bonne catégorie,
bon motif), et aucun ticket en trop. Les tickets sont créés dans un stockage temporaire :
le vrai dossier tickets/ n'est pas touché.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from support_agent.config import EVAL, MODELS, get_settings
from support_agent.conversation import Action, Conversation, Modele, Moteur
from support_agent.modele import ModeleSupport
from support_agent.tickets import Tickets

FICHIER = EVAL / "conversations.json"


def charger_conversations(chemin: Path = FICHIER) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = json.loads(chemin.read_text(encoding="utf-8"))
    for s in scenarios:
        for t in s["tours"]:
            if ("message" in t) == ("action" in t):
                raise ValueError(f"{s['id']} : chaque tour a un message OU une action")
            if "action" in t:
                Action(t["action"])  # lève une erreur si l'action est inconnue
    return scenarios


def rejouer(scenario: dict[str, Any], moteur: Moteur) -> dict[str, Any]:
    conv = Conversation()
    for tour in scenario["tours"]:
        if "message" in tour:
            moteur.repondre(conv, tour["message"])
        else:
            moteur.repondre(conv, action=Action(tour["action"]))
    t = moteur.tickets.obtenir(conv.ticket_id) if moteur.tickets and conv.ticket_id else None
    attendu = scenario["attendu"]
    resultat: dict[str, Any] = {
        "id": scenario["id"], "role": scenario["role"], "etat_final": str(conv.etat),
        "ticket_attendu": attendu["ticket"], "ticket": t.id if t else None,
        "categorie": t.categorie if t else (conv.prediction or {}).get("categorie"),
        "motif": t.motif if t else None, "groupe": t.groupe if t else None,
    }
    if attendu["ticket"]:
        resultat["correct"] = bool(t) and t is not None and (
            t.categorie == attendu["categorie"] and t.motif == attendu["motif"])
    else:
        resultat["correct"] = t is None and str(conv.etat) == attendu["etat"]
    return resultat


def bilan(modele: Modele, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    moteur = Moteur(modele, Tickets(None))
    details = [rejouer(s, moteur) for s in scenarios]
    attendus = [d for d in details if d["ticket_attendu"]]
    crees = [d for d in details if d["ticket"]]
    return {
        "conversations": len(details),
        "tickets_attendus": len(attendus),
        "tickets_crees": len(crees),
        "tickets_corrects": sum(d["correct"] for d in attendus),
        "tickets_en_trop": sum(1 for d in crees if not d["ticket_attendu"]),
        "tickets_manques": sum(1 for d in attendus if not d["ticket"]),
        "conversations_conformes": sum(d["correct"] for d in details),
        "details": details,
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, default=MODELS / "bilan_tickets.json")
    args = p.parse_args(argv)
    modele = ModeleSupport.charger()
    modele.hyper = type(modele.hyper)(**{**modele.hyper.__dict__,
                                         "seuil": get_settings().seuil_abstention})
    res = bilan(modele, charger_conversations())
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    for d in res["details"]:
        ok = "OK " if d["correct"] else "KO "
        print(f"{ok} {d['id']} {d['role']:28s} -> {d['etat_final']:17s} "
              f"ticket={d['ticket'] or '-':9s} {d['categorie'] or '-':13s} {d['motif'] or ''}")
    print(f"\n{res['tickets_crees']} tickets créés / {res['tickets_attendus']} attendus · "
          f"{res['tickets_corrects']} corrects · {res['tickets_en_trop']} en trop · "
          f"{res['tickets_manques']} manqués · conversations conformes "
          f"{res['conversations_conformes']}/{res['conversations']}")


if __name__ == "__main__":  # pragma: no cover
    main()
