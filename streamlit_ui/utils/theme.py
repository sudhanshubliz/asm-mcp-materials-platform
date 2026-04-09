from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.set_page_config(
        page_title="ASM Materials Copilot",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
            --asm-bg: #f3f5f2;
            --asm-panel: rgba(255, 255, 255, 0.78);
            --asm-panel-strong: #ffffff;
            --asm-ink: #14211d;
            --asm-muted: #54625a;
            --asm-accent: #0f8b6d;
            --asm-accent-soft: rgba(15, 139, 109, 0.12);
            --asm-line: rgba(20, 33, 29, 0.08);
            --asm-warm: #cc6b34;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(15, 139, 109, 0.10), transparent 30%),
                radial-gradient(circle at top left, rgba(204, 107, 52, 0.10), transparent 22%),
                linear-gradient(180deg, #f7f8f5 0%, var(--asm-bg) 100%);
            color: var(--asm-ink);
            font-family: 'Space Grotesk', sans-serif;
        }

        .stApp, .stMarkdown, .stText, .stDataFrame, .stChatMessage {
            color: var(--asm-ink);
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(248, 249, 245, 0.92);
            border-right: 1px solid var(--asm-line);
        }

        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: -0.02em;
            color: var(--asm-ink);
        }

        code, pre, .stCodeBlock {
            font-family: 'IBM Plex Mono', monospace !important;
        }

        .asm-hero-shell {
            padding: 0.4rem 0 0.8rem 0;
        }

        .asm-hero {
            max-width: 64rem;
            padding: 1.2rem 0 1rem 0;
        }

        .asm-kicker {
            color: var(--asm-warm);
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 700;
        }

        .asm-title {
            font-size: 2.6rem;
            line-height: 0.95;
            margin: 0.25rem 0 0.8rem 0;
            max-width: 12ch;
        }

        .asm-subtitle {
            color: var(--asm-muted);
            font-size: 1.04rem;
            line-height: 1.6;
            max-width: 60ch;
        }

        .asm-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            border-radius: 999px;
            padding: 0.35rem 0.8rem;
            background: var(--asm-accent-soft);
            color: var(--asm-accent);
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.7rem;
        }

        .asm-feature-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 1rem;
        }

        .asm-feature-row span {
            display: inline-flex;
            align-items: center;
            border: 1px solid rgba(20, 33, 29, 0.08);
            border-radius: 999px;
            padding: 0.42rem 0.8rem;
            background: rgba(255, 255, 255, 0.58);
            color: var(--asm-ink);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .asm-result {
            border-top: 1px solid var(--asm-line);
            padding-top: 1rem;
            margin-top: 1rem;
        }

        .asm-caption {
            color: var(--asm-muted);
            font-size: 0.88rem;
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] {
            position: sticky;
            top: 0.55rem;
            z-index: 40;
            max-width: 72rem;
            padding-top: 0.3rem;
            padding-bottom: 0.75rem;
            background: linear-gradient(180deg, rgba(243, 245, 242, 0.99) 0%, rgba(243, 245, 242, 0.95) 82%, rgba(243, 245, 242, 0) 100%);
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] [data-testid="stForm"] {
            border: 1px solid var(--asm-line);
            border-radius: 26px;
            padding: 0.65rem 0.7rem 0.35rem;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(18px);
            box-shadow: 0 18px 42px rgba(20, 33, 29, 0.08);
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] input {
            border-radius: 18px !important;
            border: 1px solid rgba(20, 33, 29, 0.1) !important;
            background: rgba(247, 248, 245, 0.9) !important;
            min-height: 3.25rem;
            padding-left: 0.75rem !important;
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] button[kind="secondaryFormSubmit"] {
            border-radius: 18px;
            min-height: 3.25rem;
            background: var(--asm-accent);
            color: white;
            border: none;
            font-weight: 700;
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] [data-testid="stCaptionContainer"] {
            margin-top: 0.15rem;
            margin-bottom: 0.25rem;
        }

        div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] button[kind="secondary"] {
            min-height: 2.5rem;
            border-radius: 999px;
            border: 1px solid rgba(20, 33, 29, 0.08);
            background: rgba(255, 255, 255, 0.78);
            color: var(--asm-ink);
            font-weight: 500;
        }

        [data-testid="stChatMessage"] {
            max-width: 72rem;
        }

        [data-testid="stChatMessageContent"] {
            border-radius: 18px;
        }

        @media (max-width: 900px) {
            div[data-testid="stElementContainer"]:has(#asm-sticky-search-anchor) + div[data-testid="stElementContainer"] {
                top: 0.25rem;
            }

            .asm-title {
                font-size: 2.2rem;
            }

            .asm-subtitle {
                font-size: 0.98rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
