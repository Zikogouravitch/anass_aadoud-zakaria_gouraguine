"""Interface de l'agent (onglet Chat).

    streamlit run support_agent/ui/app.py     # l'API doit tourner (API_URL dans .env)
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from support_agent.ui.client import ClientAPI, ErreurAPI

LIBELLES = {
    "resolu": "✅ Solved",
    "non_resolu": "❌ Not solved",
    "technicien": "🧑‍🔧 Talk to a technician",
    "annuler": "Cancel",
}
COULEURS_PRIORITE = {"high": "red", "medium": "orange", "low": "green"}


@st.cache_resource
def client() -> ClientAPI:
    return ClientAPI()


def _etat() -> Any:
    s = st.session_state
    s.setdefault("conversation_id", None)
    s.setdefault("tours", [])  # liste de (role, texte)
    s.setdefault("derniere", None)  # dernière réponse de l'API
    s.setdefault("erreur", None)
    return s


def envoyer(message: str | None = None, action: str | None = None) -> None:
    s = _etat()
    if message:
        s.tours.append(("user", message))
    try:
        rep = client().chat(message, s.conversation_id, action)
    except ErreurAPI as e:
        s.erreur = str(e)
        return
    s.erreur = None
    s.conversation_id = rep["conversation_id"]
    s.derniere = rep
    s.tours.append(("assistant", rep["message"]))


def nouvelle_conversation() -> None:
    s = _etat()
    s.conversation_id, s.tours, s.derniere, s.erreur = None, [], None, None


def bandeau(rep: dict[str, Any]) -> None:
    p = rep.get("prediction") or {}
    if not p:
        return
    couleur = COULEURS_PRIORITE.get(p.get("priorite", ""), "gray")
    critique = " · :red[**critical**]" if p.get("critique") else ""
    st.caption(f"Category **{p['categorie']}** ({p['confiance']:.0%}) · priority "
               f":{couleur}[{p['priorite']}]{critique}"
               + (f" · attempt {rep['tentative']}" if rep.get("tentative") else ""))


def onglet_chat() -> None:
    s = _etat()
    for role, texte in s.tours:
        with st.chat_message(role):
            st.markdown(texte.replace("\n", "  \n"))
    rep = s.derniere
    if rep:
        bandeau(rep)
        if rep.get("brouillon_ticket"):
            b = rep["brouillon_ticket"]
            with st.expander("Pre-filled ticket", expanded=True):
                st.table({"Field": ["Category", "Priority", "Reason", "Articles tried",
                                    "Description"],
                          "Value": [b["categorie"], b["priorite"], b["motif"],
                                    ", ".join(b["articles_essayes"]) or "—", b["description"]]})
                st.caption("Ticket creation after your confirmation comes with /tickets (T6).")
        colonnes = st.columns(max(1, len(rep.get("actions", []))))
        for col, action in zip(colonnes, rep.get("actions", []), strict=False):
            if action in LIBELLES:
                col.button(LIBELLES[action], key=f"{action}-{len(s.tours)}",
                           on_click=envoyer, kwargs={"action": action})
    if s.erreur:
        st.error(s.erreur)
    message = st.chat_input("Describe your IT problem (in English)")
    if message:
        envoyer(message=message)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="IT support agent", page_icon="🛠️")
    st.title("IT support agent")
    st.sidebar.button("New conversation", on_click=nouvelle_conversation)
    st.sidebar.caption("Level-1 IT support. Answers come from validated knowledge-base "
                       "articles; critical cases go straight to a technician.")
    (chat,) = st.tabs(["Chat"])
    with chat:
        onglet_chat()


main()
