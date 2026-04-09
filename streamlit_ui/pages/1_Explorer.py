from __future__ import annotations

import streamlit as st

from streamlit_ui.components.result_cards import render_result
from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.services.mcp_client import MCPClientError, MCPClientService
from streamlit_ui.services.normalizers import normalize_mcp_response
from streamlit_ui.utils.session import initialize_state, push_recent_query
from streamlit_ui.utils.theme import apply_theme


@st.cache_resource(show_spinner=False)
def get_client() -> MCPClientService:
    return MCPClientService()


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.title("Explorer")
    st.caption("Structured search over the remote MCP endpoint.")

    with st.form("explorer-form"):
        col1, col2, col3 = st.columns(3)
        formula = col1.text_input("Formula", placeholder="LiFePO4")
        elements = col2.text_input("Elements", placeholder="Si,O")
        crystal_system = col3.selectbox(
            "Crystal system",
            options=["", "cubic", "hexagonal", "tetragonal", "trigonal", "orthorhombic", "monoclinic", "triclinic"],
        )

        col4, col5, col6 = st.columns(3)
        band_gap_min = col4.number_input("Band gap min", value=0.0, step=0.1)
        band_gap_max = col5.number_input("Band gap max", value=0.0, step=0.1)
        stable_only = col6.toggle("Stable only", value=False)

        submitted = st.form_submit_button("Run explorer search", use_container_width=True)

    if submitted:
        arguments = {"query": "Explorer search", "limit": 25, "offset": 0}
        if formula:
            arguments["formula"] = formula
        if elements:
            arguments["elements"] = [item.strip() for item in elements.split(",") if item.strip()]
        if crystal_system:
            arguments["crystal_system"] = crystal_system
        if band_gap_min > 0:
            arguments["band_gap_min"] = band_gap_min
        if band_gap_max > 0:
            arguments["band_gap_max"] = band_gap_max
        if stable_only:
            arguments["is_stable"] = True

        if len(arguments) == 3:
            st.warning("Add at least one filter before running Explorer search.")
            return

        try:
            client = get_client()
            raw = client.call_tool("search_materials_advanced_tool", arguments, use_cache=True)
            normalized = normalize_mcp_response("search_materials_advanced_tool", raw, "Explorer search")
            push_recent_query(st.session_state, f"Explorer: {arguments}")
            render_result(
                normalized,
                show_raw_json=st.session_state.show_raw_json,
                compact_mode=st.session_state.compact_mode,
            )
        except MCPClientError as exc:
            st.error(str(exc))


if __name__ == "__main__":
    main()
