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
        st.warning(status.error if status.ok else status.error)

    qdrant = get_client().qdrant_health()
    qdrant_label = "OK" if qdrant.get("ok") else "Unavailable"
    st.metric("Qdrant", qdrant_label)
    q_cols = st.columns(3)
    q_cols[0].metric("Collection", qdrant.get("collection") or "N/A")
    q_cols[1].metric("Points", qdrant.get("points_count") if qdrant.get("points_count") is not None else "N/A")
    q_cols[2].metric("Embedding", qdrant.get("inference_model") or "N/A")

    if qdrant.get("error"):
        st.warning("Qdrant nearest-neighbor search is not ready. Expand the payload for details.")

    tool_tab, health_tab, qdrant_tab = st.tabs(["Tools", "Health payload", "Qdrant"])
    with tool_tab:
        st.write(status.tools or [])
    with health_tab:
        st.json(status.health or {}, expanded=False)
    with qdrant_tab:
        st.json(qdrant, expanded=False)


if __name__ == "__main__":
    main()
