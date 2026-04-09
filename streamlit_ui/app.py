from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from streamlit_ui.components.result_cards import render_result
from streamlit_ui.components.sidebar import render_sidebar
from streamlit_ui.services.mcp_client import MCPClientError, MCPClientService
from streamlit_ui.services.normalizers import normalize_comparison_response, normalize_mcp_response
from streamlit_ui.services.query_parser import parse_user_query
from streamlit_ui.utils.session import initialize_state, push_recent_query, save_query
from streamlit_ui.utils.theme import apply_theme


@st.cache_resource(show_spinner=False)
def get_client() -> MCPClientService:
    return MCPClientService()


def _run_prompt(prompt: str) -> None:
    client = get_client()
    plan = parse_user_query(prompt)
    push_recent_query(st.session_state, prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Querying the MCP server..."):
            try:
                if plan.intent == "compare":
                    records = client.compare_materials(plan.compare_targets)
                    normalized = normalize_comparison_response(records, prompt)
                else:
                    raw = client.call_tool(plan.tool_name, plan.arguments)
                    normalized = normalize_mcp_response(plan.tool_name, raw, prompt)
                render_result(
                    normalized,
                    show_raw_json=st.session_state.show_raw_json,
                    compact_mode=st.session_state.compact_mode,
                )
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": prompt,
                    }
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": normalized,
                    }
                )
            except MCPClientError as exc:
                st.error(str(exc))


def _render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_result(
                    message["content"],
                    show_raw_json=st.session_state.show_raw_json,
                    compact_mode=st.session_state.compact_mode,
                )
            else:
                st.markdown(message["content"])


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.markdown(
        """
        <div class="asm-hero">
            <div class="asm-badge">Remote MCP workflow</div>
            <div class="asm-kicker">ASM Materials Copilot</div>
            <h1 class="asm-title">Chat with your Materials Project server.</h1>
            <p class="asm-subtitle">
                Search formulas, inspect mp-ids, compare materials, and export normalized results without relying on local MCP config files.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    shell = st.container()
    with shell:
        _render_chat_history()

        prompt = st.chat_input("Ask about formulas, mp-ids, band gaps, cathodes, alloys, or comparisons")
        if st.session_state.pending_prompt and not prompt:
            prompt = st.session_state.pending_prompt
            st.session_state.pending_prompt = None

        if prompt:
            _run_prompt(prompt)

    action_columns = st.columns([3, 1])
    with action_columns[1]:
        if st.button("Save last prompt", use_container_width=True):
            if st.session_state.messages:
                last_user_message = next(
                    (item["content"] for item in reversed(st.session_state.messages) if item["role"] == "user"),
                    None,
                )
                if last_user_message:
                    save_query(st.session_state, last_user_message)
                    st.toast("Last query saved")


if __name__ == "__main__":
    main()
