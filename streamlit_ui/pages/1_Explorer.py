from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


PRESETS = {
    "Custom": {},
    "Semiconductors": {"band_gap_min": 0.1, "band_gap_max": 3.5, "material_type": "Non-metal"},
    "Stable oxides": {"elements": "O", "stable_only": True},
    "Battery cathodes": {"elements": "Li,O", "stable_only": True},
    "Lightweight alloys": {"density_max": 5.0, "material_type": "Metal"},
}


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.title("Explorer")
    st.caption("Build a structured Materials Project search with scientific filters and exportable results.")

    with st.form("explorer-form"):
        preset = st.selectbox("Preset", options=list(PRESETS.keys()), help="Start from a common materials search pattern.")
        preset_values = PRESETS[preset]
        col1, col2, col3 = st.columns(3)
        formula = col1.text_input("Formula", placeholder="LiFePO4")
        elements = col2.text_input("Elements", value=str(preset_values.get("elements", "")), placeholder="Si,O")
        crystal_system = col3.selectbox(
            "Crystal system",
            options=["", "cubic", "hexagonal", "tetragonal", "trigonal", "orthorhombic", "monoclinic", "triclinic"],
        )

        col4, col5, col6, col7 = st.columns(4)
        band_gap_min = col4.number_input(
            "Band gap min (eV)",
            value=float(preset_values.get("band_gap_min", 0.0)),
            min_value=0.0,
            step=0.1,
            help="Leave at 0.0 when you do not need a lower band-gap bound.",
        )
        band_gap_max = col5.number_input(
            "Band gap max (eV)",
            value=float(preset_values.get("band_gap_max", 0.0)),
            min_value=0.0,
            step=0.1,
            help="Leave at 0.0 when you do not need an upper band-gap bound.",
        )
        density_max = col6.number_input(
            "Density max (g/cm3)",
            value=float(preset_values.get("density_max", 0.0)),
            min_value=0.0,
            step=0.1,
            help="Useful for lightweight materials. Leave at 0.0 to ignore density.",
        )
        stable_only = col7.toggle("Stable only", value=bool(preset_values.get("stable_only", False)))
        material_type = st.segmented_control(
            "Material type",
            options=["Any", "Metal", "Non-metal"],
            default=str(preset_values.get("material_type", "Any")),
        )

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
        if density_max > 0:
            arguments["density_max"] = density_max
        if stable_only:
            arguments["is_stable"] = True
        if material_type == "Metal":
            arguments["is_metal"] = True
        elif material_type == "Non-metal":
            arguments["is_metal"] = False

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
                key_prefix="explorer-result",
            )
        except MCPClientError as exc:
            st.error(str(exc))
            if st.session_state.debug_mode and exc.detail:
                with st.expander("Debug details", expanded=False):
                    st.code(exc.detail)


if __name__ == "__main__":
    main()
