"""Ask Notes page: tutor chat that answers only from the chosen chapters."""

import streamlit as st

from actions.ask_question import get_answer
from config import LANGUAGES
from services.tts import text_to_speech
from state import chapter_name, go_to, log_activity
from ui.components import copy_button, language_selector, page_header, thinking_indicator, user_bubble
from utils.text import friendly_error, strip_markdown


def render():
    page_header("Ask Notes", "A friendly tutor that answers only from the chapters you choose.")
    library = st.session_state.library
    if not library:
        with st.container(key="card_ask_empty"):
            st.markdown("**Upload your notes first.**")
            st.caption("Upload your PDFs on the Notes page, then come back to ask questions.")
            st.button("Go to Notes", icon=":material/description:", type="primary", on_click=go_to, args=("Notes",))
        return

    # Settings: which chapters (required) and which language
    chapters_col, lang_col = st.columns([3, 1], vertical_alignment="bottom")
    with chapters_col:
        st.multiselect(
            "Chapters to ask about",
            list(library),
            key="chat_files",
            persist_state="session",
            placeholder="Choose at least one chapter",
        )
    with lang_col:
        language_selector("ask")
    chosen = st.session_state.chat_files

    # The chat box is pinned to the bottom of the page
    question = st.chat_input(
        "Ask about your chapters..." if chosen else "Choose at least one chapter first",
        key="chat_box",
        disabled=not chosen,
    )
    # A clicked option chip also counts as a question
    question = question or st.session_state.pop("chip_question", None)

    with st.container(key="chat_area"):
        if not st.session_state.chat:
            st.caption("Try: \"What is the difference between a fault and a failure?\" or \"Explain chapter 1\".")
        show_chat()
        if question and chosen:
            send_question(question)


def show_chat():
    """Show the conversation: student on the right, QuickStudy on the left."""
    chat = st.session_state.chat
    if not chat:
        return

    # Header row with "Clear chat" on the right
    title_col, clear_col = st.columns([4, 1], vertical_alignment="center")
    title_col.markdown('<div class="qs-label" style="margin:0">Conversation</div>', unsafe_allow_html=True)
    if clear_col.button("Clear chat", icon=":material/delete_sweep:", type="tertiary", key="clear_chat"):
        st.session_state.chat = []
        st.session_state.chat_audio = {}
        st.rerun()

    for i, msg in enumerate(chat):
        if msg["role"] == "user":
            user_bubble(msg["content"])
            continue
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            if msg.get("error"):
                st.error(msg["content"])
                continue
            st.markdown(msg["content"])

            # "Which part?" question: show the sections as clickable chips (latest message only)
            if msg.get("type") == "clarify" and i == len(chat) - 1:
                with st.container(horizontal=True, gap="small", key=f"chips_{i}"):
                    for j, option in enumerate(msg.get("options", [])):
                        st.button(option, key=f"chip_{i}_{j}", on_click=choose_option, args=(option,))

            sources = msg.get("sources", [])
            if sources:
                with st.expander(f"📎 Sources from your notes ({len(sources)})"):
                    for source in sources:
                        st.markdown(f"> {source}")
            message_actions(i, msg)


def choose_option(option: str):
    """A chip was clicked: send it as the next question (button callback)."""
    st.session_state.chip_question = option


def message_actions(index: int, msg: dict):
    """Small grey actions under an answer: Listen · Copy · Regenerate."""
    with st.container(horizontal=True, gap="small", key=f"actions_{index}"):
        listen = st.button("🔊 Listen", key=f"listen_{index}", type="tertiary")
        copy_button(msg["content"], index)
        regenerate = st.button("🔄 Regenerate", key=f"regen_{index}", type="tertiary")

    if listen and index not in st.session_state.chat_audio:
        try:
            with st.spinner("Creating audio..."):
                st.session_state.chat_audio[index] = text_to_speech(
                    strip_markdown(msg["content"]), LANGUAGES[msg["language"]]
                )
        except Exception as e:
            st.error(f"Text-to-speech failed. {friendly_error(e)}")
    if index in st.session_state.chat_audio:
        st.audio(st.session_state.chat_audio[index], format="audio/mp3")

    if regenerate:
        regenerate_answer(index)


def send_question(question: str):
    """Save the student's question, get an answer once, then redraw the chat."""
    chat = st.session_state.chat
    chat.append({"role": "user", "content": question})
    log_activity("ask", "", ", ".join(chapter_name(f) for f in st.session_state.chat_files))
    user_bubble(question)
    with st.chat_message("assistant", avatar=":material/auto_awesome:"):
        thinking_indicator()
        chat.append(get_answer(chat))
    st.rerun()


def regenerate_answer(index: int):
    """Ask again for the answer at this position (uses the messages before it)."""
    st.session_state.chat_audio.pop(index, None)
    thinking_indicator()
    st.session_state.chat[index] = get_answer(st.session_state.chat[:index])
    st.rerun()
