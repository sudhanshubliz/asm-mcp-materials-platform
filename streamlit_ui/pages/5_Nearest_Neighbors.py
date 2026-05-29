from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.services.mcp_client import MCPClientError, MCPClientService
from streamlit_ui.utils.theme import apply_theme


@st.cache_resource(show_spinner=False)
def get_client() -> MCPClientService:
    return MCPClientService()


def _record_text(record: dict) -> str:
    text = record.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    payload = record.get("payload") or {}
    if not isinstance(payload, dict):
        return ""

    for field_name in ("text", "content", "page_content", "document", "chunk", "summary", "abstract"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def main() -> None:
    apply_theme()
    render_sidebar()

    st.title("Nearest Neighbors")
    st.caption("Search your Qdrant collection through the MCP server and inspect matching text chunks.")

    with st.form("nearest-neighbors-form"):
        query = st.text_area(
            "Query text",
            placeholder="Example: stable cathode materials for lithium batteries",
            height=120,
        )
        top_k = st.slider("Neighbors", min_value=1, max_value=20, value=5)
        submitted = st.form_submit_button("Search", use_container_width=True)

    if not submitted:
        return

    if not query.strip():
        st.warning("Enter a query first.")
        return

    try:
        with st.spinner("Searching nearest neighbors..."):
            payload = get_client().call_tool(
                "rag_search_tool",
                {"question": query.strip(), "top_k": top_k},
                use_cache=False,
            )
    except MCPClientError as exc:
        st.error(str(exc))
        return

    records = payload.get("data", [])
    if not records:
        st.info("No nearest neighbors returned.")
        with st.expander("Raw response", expanded=False):
            st.json(payload, expanded=False)
        return

    st.metric("Matches", len(records))
    st.dataframe(records, use_container_width=True, hide_index=True)

    for index, record in enumerate(records, start=1):
        label = f"{index}. {record.get('id', 'neighbor')} - score {record.get('score', 'N/A')}"
        with st.expander(label, expanded=index == 1):
            text = _record_text(record)
            if text:
                st.markdown(text)
            else:
                st.caption("No text field found in this payload.")
            st.json(record.get("payload") or {}, expanded=False)

    with st.expander("Raw response", expanded=False):
        st.json(payload, expanded=False)


if __name__ == "__main__":
    main()
