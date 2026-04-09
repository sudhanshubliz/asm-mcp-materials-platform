from __future__ import annotations

import streamlit as st

from streamlit_ui.components.result_cards import render_result
from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.services.mcp_client import MCPClientService
from streamlit_ui.services.normalizers import normalize_comparison_response
from streamlit_ui.utils.session import initialize_state, push_recent_query
from streamlit_ui.utils.theme import apply_theme


@st.cache_resource(show_spinner=False)
def get_client() -> MCPClientService:
    return MCPClientService()


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.title("Compare")
    st.caption("Compare 2 to 5 materials by formula or mp-id.")

    targets = st.text_area(
        "Materials",
        placeholder="Si, GaAs, mp-149",
        help="Separate each material with a comma.",
    )

    if st.button("Compare materials", use_container_width=True):
        parsed_targets = [item.strip() for item in targets.split(",") if item.strip()]
        records = get_client().compare_materials(parsed_targets)
        push_recent_query(st.session_state, f"Compare: {', '.join(parsed_targets)}")
        result = normalize_comparison_response(records, f"Compare {' vs '.join(parsed_targets)}")
        render_result(
            result,
            show_raw_json=st.session_state.show_raw_json,
            compact_mode=st.session_state.compact_mode,
        )


if __name__ == "__main__":
    main()
