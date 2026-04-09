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
from streamlit_ui.utils.constants import SAMPLE_PROMPTS
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
                    key_prefix=f"live-{len(st.session_state.messages)}",
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
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_result(
                    message["content"],
                    show_raw_json=st.session_state.show_raw_json,
                    compact_mode=st.session_state.compact_mode,
                    key_prefix=f"history-{index}",
                )
            else:
                st.markdown(message["content"])


def _render_top_search() -> str | None:
    if "top_search_query" not in st.session_state:
        st.session_state.top_search_query = ""

    queued_prompt = st.session_state.pending_prompt
    if queued_prompt:
        st.session_state.top_search_query = queued_prompt
        st.session_state.pending_prompt = None

    st.markdown('<div id="asm-sticky-search-anchor"></div>', unsafe_allow_html=True)
    with st.form("asm-top-search-form", clear_on_submit=False, border=False):
        search_columns = st.columns([6, 1.35], vertical_alignment="center")
        with search_columns[0]:
            st.text_input(
                "Search materials",
                key="top_search_query",
                placeholder="Search formulas, mp-ids, stable cathodes, band gaps, alloys, and more",
                label_visibility="collapsed",
            )
        with search_columns[1]:
            submitted = st.form_submit_button("Search", use_container_width=True)

    st.caption("Try a quick start or write your own question in natural language.")
    quick_actions = [
        ("Aerospace alloys", SAMPLE_PROMPTS[0]),
        ("Si vs GaAs", SAMPLE_PROMPTS[1]),
        ("Band gap filter", SAMPLE_PROMPTS[2]),
        ("Battery cathodes", SAMPLE_PROMPTS[3]),
        ("mp-149 lookup", SAMPLE_PROMPTS[4]),
    ]
    clicked_prompt: str | None = None
    action_columns = st.columns(len(quick_actions))
    for column, (label, full_prompt) in zip(action_columns, quick_actions, strict=False):
        with column:
            if st.button(label, key=f"hero-prompt::{label}", use_container_width=True):
                st.session_state.top_search_query = full_prompt
                save_query(st.session_state, full_prompt)
                clicked_prompt = full_prompt

    if queued_prompt:
        return queued_prompt
    if clicked_prompt:
        return clicked_prompt
    if submitted:
        return st.session_state.top_search_query.strip()
    return None


def main() -> None:
    apply_theme()
    initialize_state(st.session_state)
    render_sidebar()

    st.markdown(
        """
        <section class="asm-hero-shell">
            <div class="asm-hero">
                <div class="asm-hero-visual" aria-hidden="true">
                    <svg viewBox="0 0 320 180" role="img">
                        <defs>
                            <linearGradient id="asmOrb" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#0f8b6d" />
                                <stop offset="100%" stop-color="#cc6b34" />
                            </linearGradient>
                            <linearGradient id="asmBeam" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="rgba(15,139,109,0.08)" />
                                <stop offset="100%" stop-color="rgba(204,107,52,0.15)" />
                            </linearGradient>
                        </defs>
                        <rect x="22" y="26" width="276" height="128" rx="30" fill="rgba(255,255,255,0.72)" stroke="rgba(20,33,29,0.08)" />
                        <path d="M70 118 L118 64 L164 102 L214 56 L256 94" fill="none" stroke="url(#asmBeam)" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" />
                        <circle cx="70" cy="118" r="13" fill="#ffffff" stroke="#0f8b6d" stroke-width="6" />
                        <circle cx="118" cy="64" r="15" fill="#ffffff" stroke="#cc6b34" stroke-width="6" />
                        <circle cx="164" cy="102" r="12" fill="#ffffff" stroke="#0f8b6d" stroke-width="6" />
                        <circle cx="214" cy="56" r="16" fill="#ffffff" stroke="#14211d" stroke-width="6" />
                        <circle cx="256" cy="94" r="13" fill="#ffffff" stroke="#0f8b6d" stroke-width="6" />
                        <circle cx="237" cy="126" r="30" fill="url(#asmOrb)" opacity="0.18" />
                        <path d="M95 132 C132 105, 176 104, 222 132" fill="none" stroke="rgba(20,33,29,0.12)" stroke-width="4" stroke-linecap="round" />
                    </svg>
                </div>
                <div class="asm-badge">Remote MCP workflow</div>
                <div class="asm-kicker">ASM Materials Copilot</div>
                <h1 class="asm-title">Chat with your Materials Project server.</h1>
                <p class="asm-subtitle">
                    Search formulas, inspect mp-ids, compare materials, and export normalized results through your remote MCP endpoint.
                </p>
                <div class="asm-feature-row">
                    <span>Formula search</span>
                    <span>mp-id lookup</span>
                    <span>Property filters</span>
                    <span>Compare and export</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    prompt = _render_top_search()

    shell = st.container()
    with shell:
        _render_chat_history()

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
