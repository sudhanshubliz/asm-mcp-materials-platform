from __future__ import annotations

from streamlit.runtime.state import SessionStateProxy

from streamlit_ui.utils.constants import MAX_RECENT_SEARCHES, MAX_SAVED_QUERIES


def initialize_state(session_state: SessionStateProxy) -> None:
    defaults = {
        "messages": [],
        "recent_searches": [],
        "saved_queries": [],
        "pending_prompt": None,
        "debug_mode": False,
        "show_raw_json": False,
        "compact_mode": False,
    }
    for key, value in defaults.items():
        session_state.setdefault(key, value)


def push_recent_query(session_state: SessionStateProxy, query: str) -> None:
    recent = [item for item in session_state.recent_searches if item != query]
    session_state.recent_searches = [query, *recent][:MAX_RECENT_SEARCHES]


def save_query(session_state: SessionStateProxy, query: str) -> None:
    saved = [item for item in session_state.saved_queries if item != query]
    session_state.saved_queries = [query, *saved][:MAX_SAVED_QUERIES]
