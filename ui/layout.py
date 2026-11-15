"""Page layout: CSS, greeting and the sidebar."""

from datetime import datetime
import html
from pathlib import Path

import streamlit as st

from actions.manage_library import remove_from_library
from actions.sync_data import db_status
from config import GEMINI, GROQ_FAST, GROQ_MAIN, PAGES
from state import go_to, start_over
from utils.text import page_count, slug

CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "styles.css"


def load_css():
    """Load all custom styling from assets/styles.css."""
    st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def current_student_name() -> str:
    """The student's name. After a refresh the session is empty, so the name is read back
    from the page URL (?user=...) and their saved data is loaded again."""
    if not st.session_state.get("student_name") and st.query_params.get("user"):
        st.session_state.student_name = st.query_params["user"]
    return (st.session_state.get("student_name") or "").strip()


def remember_name(name: str):
    """Save the name in the session and in the URL (?user=...), so a refresh keeps the same user."""
    name = (name or "").strip()
    st.session_state.student_name = name
    if name:
        st.query_params["user"] = name
    elif "user" in st.query_params:
        del st.query_params["user"]


def start_over_and_forget_name():
    """"Start over" button: clear the session and the name in the URL."""
    if "user" in st.query_params:
        del st.query_params["user"]
    start_over()


def hero(subtitle: str):
    """The glowing orb, "Good <time>, <name>" and a short subtitle."""
    name = current_student_name() or "Student"
    st.markdown(
        f"""
<div class="qs-hero">
    <div class="qs-orb"></div>
    <div class="qs-greeting">{greeting()}, {html.escape(name)}</div>
    <div class="qs-subtitle">{html.escape(subtitle)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def greeting() -> str:
    """Good Morning / Afternoon / Evening, based on the current time."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    if hour < 18:
        return "Good Afternoon"
    return "Good Evening"


def show_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="qs-logo"><div class="qs-logo-orb"></div>QuickStudy</div>',
            unsafe_allow_html=True,
        )

        for page, icon in PAGES.items():
            is_open = st.session_state.page == page
            st.button(
                page,
                icon=icon,
                key=f"nav_{slug(page)}",
                type="primary" if is_open else "secondary",
                width="stretch",
                on_click=go_to,
                args=(page,),
            )

        # My Notes: every uploaded PDF, each with a remove (x) button
        st.markdown('<div class="qs-side-label">My Notes</div>', unsafe_allow_html=True)
        if not st.session_state.library:
            st.caption("No PDFs yet. Upload one on the Notes page.")
        for file_id, info in st.session_state.library.items():
            name_col, remove_col = st.columns([5, 1], vertical_alignment="center", gap="small")
            name_col.markdown(
                f'<div class="qs-file" title="{html.escape(info["name"])}">📄 {html.escape(info["name"])}'
                f'<br><small>{page_count(info)}</small></div>',
                unsafe_allow_html=True,
            )
            remove_col.button(
                ":material/close:",
                key=f"remove_{file_id}",
                type="tertiary",
                help=f"Remove {info['name']}",
                on_click=remove_from_library,
                args=(file_id,),
            )

        with st.container(key="sidebar_bottom"):
            st.text_input("Your name", key="student_name", placeholder="Student",
                          help="Your notes, quizzes and plan are saved under this name.",
                          on_change=lambda: remember_name(st.session_state.student_name))
            status = db_status()
            if status == "offline":
                st.warning("Offline mode: data will not be saved", icon=":material/cloud_off:")
            elif status == "no_name":
                st.caption("Type your name to save your progress.")
            else:
                st.caption("✓ Your progress is saved.")
            with st.expander("AI Tools Used", icon=":material/auto_awesome:"):
                st.markdown(f"""
**Groq (main AI)** · `{GROQ_MAIN}`
The primary AI: fast, with higher free limits. Writes the chapter
outlines, study notes, quizzes and revision quizzes (checked for a
correct answer key), the AI Study Planner tasks, and the detailed
"Explain more" explanations.

**Groq (fast AI)** · `{GROQ_FAST}`
A smaller, faster model for the Ask Notes chat (answers only from your
chapters, and asks which part you mean for broad questions) and the
AI Audio Tutor scripts.

**Google Gemini** · `{GEMINI}`
The backup: if Groq is busy or fails, Gemini does the same task. It also
reads scanned PDFs with Gemini Vision.

**gTTS** · Google Text-to-Speech
Speaks the Audio Tutor lessons and chat answers in English or
Bahasa Melayu.

**sumy** · TextRank (runs locally)
Offline backup summary if no AI is available.

**Supabase** · database (PostgreSQL)
Saves your chapters, outlines, study notes, quiz results, reported
questions, exam date and study plan under your name, so they are still
there after a refresh (and the AI is not asked again).
""")
            st.button("Start over", icon=":material/restart_alt:", width="stretch",
                      on_click=start_over_and_forget_name)
