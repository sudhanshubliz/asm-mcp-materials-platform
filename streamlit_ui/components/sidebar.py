from __future__ import annotations

import streamlit as st

from streamlit_ui.services.mcp_client import MCPClientService
from streamlit_ui.utils.constants import SAMPLE_PROMPTS
from streamlit_ui.utils.session import save_query

HOME_PAGE = "app.py"


@st.cache_resource(show_spinner=False)
def get_sidebar_client() -> MCPClientService:
    return MCPClientService()


@st.cache_data(ttl=20, show_spinner=False)
def get_cached_connection_status() -> dict[str, object]:
    status = get_sidebar_client().health_check()
    return {
        "ok": status.ok,
        "latency_ms": status.latency_ms,
        "tools": status.tools,
        "health": status.health,
        "endpoint": status.endpoint,
        "error": status.error,
    }


def render_sidebar() -> None:
    status = get_cached_connection_status()
    with st.sidebar:
        st.markdown("### Connection")
        badge = "Connected" if status["ok"] else "Unavailable"
        st.caption(f"{badge} • {status['latency_ms']} ms")
        st.caption(status["endpoint"])
        if status["error"]:
            st.error(str(status["error"]))

        st.markdown("### Example prompts")
        for prompt in SAMPLE_PROMPTS:
            if st.button(prompt, key=f"prompt::{prompt}", use_container_width=True):
                st.session_state.pending_prompt = prompt
                save_query(st.session_state, prompt)
                st.switch_page(HOME_PAGE)

        st.markdown("### Recent searches")
        for recent in st.session_state.recent_searches[:5]:
            if st.button(recent, key=f"recent::{recent}", use_container_width=True):
                st.session_state.pending_prompt = recent
                st.switch_page(HOME_PAGE)

        st.markdown("### Saved queries")
        for saved in st.session_state.saved_queries[:5]:
            col1, col2 = st.columns([5, 1])
            if col1.button(saved, key=f"saved::{saved}", use_container_width=True):
                st.session_state.pending_prompt = saved
                st.switch_page(HOME_PAGE)
            if col2.button("★", key=f"star::{saved}", use_container_width=True):
                st.toast(f"Saved query pinned: {saved}")

        st.markdown("### Display")
        st.session_state.debug_mode = st.toggle("Debug mode", value=st.session_state.debug_mode)
        st.session_state.show_raw_json = st.toggle("Raw JSON", value=st.session_state.show_raw_json)
        st.session_state.compact_mode = st.toggle("Compact mode", value=st.session_state.compact_mode)
