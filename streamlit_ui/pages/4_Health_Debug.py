from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.services.mcp_client import MCPClientService
from streamlit_ui.utils.session import initialize_state
from streamlit_ui.utils.theme import apply_theme


@st.cache_resource(show_spinner=False)
def get_client() -> MCPClientService:
    return MCPClientService()


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.title("Health & Debug")
    st.caption("Inspect connectivity to the deployed MCP server.")

    status = get_client().health_check()
    st.metric("Connection", "OK" if status.ok else "Offline")
    st.metric("Latency", f"{status.latency_ms} ms")
    st.caption(status.endpoint)

    if status.error:
        st.error(status.error)

    tool_tab, health_tab = st.tabs(["Tools", "Health payload"])
    with tool_tab:
        st.write(status.tools or [])
    with health_tab:
        st.json(status.health or {}, expanded=False)


if __name__ == "__main__":
    main()
