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

        .asm-shell {
            background: var(--asm-panel);
            border: 1px solid var(--asm-line);
            border-radius: 24px;
            padding: 1.4rem 1.5rem;
            backdrop-filter: blur(16px);
        }

        .asm-hero {
            padding: 1.2rem 0 1.2rem 0;
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
            font-size: 1rem;
            max-width: 58ch;
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

        .asm-result {
            border-top: 1px solid var(--asm-line);
            padding-top: 1rem;
            margin-top: 1rem;
        }

        .asm-caption {
            color: var(--asm-muted);
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
