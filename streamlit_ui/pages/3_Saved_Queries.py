from __future__ import annotations

import streamlit as st

from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.utils.session import initialize_state
from streamlit_ui.utils.theme import apply_theme


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.title("Saved Queries")
    st.caption("Session-level saved prompts for quick reuse.")

    if not st.session_state.saved_queries:
        st.info("No saved queries yet. Save one from the Chat page.")
        return

    for query in st.session_state.saved_queries:
        col1, col2 = st.columns([6, 1])
        if col1.button(query, key=f"saved-page::{query}", use_container_width=True):
            st.session_state.pending_prompt = query
            st.switch_page("streamlit_ui/app.py")
        if col2.button("Remove", key=f"remove::{query}", use_container_width=True):
            st.session_state.saved_queries = [item for item in st.session_state.saved_queries if item != query]
            st.rerun()


if __name__ == "__main__":
    main()
