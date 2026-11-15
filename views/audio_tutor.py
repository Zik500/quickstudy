"""Audio Tutor page: a spoken lesson about the study notes."""

import html

import streamlit as st

from actions.make_tutor_script import tutor_script_for_notes
from state import find_notes, go_to
from ui.components import audio_tutor, language_selector, notes_selector, page_header, require_library


def render():
    page_header("AI Audio Tutor", "A friendly spoken lesson about your notes, in English or Bahasa Melayu.")
    if not require_library():
        return

    file_col, lang_col = st.columns([2, 1], vertical_alignment="bottom")
    with file_col:
        notes_selector()
    with lang_col:
        language_selector("tutor")

    file_id = st.session_state.current_file
    notes = find_notes(file_id, st.session_state.tutor_language)
    if notes is None:
        with st.container(key="card_tutor_empty"):
            st.markdown(f"**The Audio Tutor explains the study notes of {html.escape(file_id)}.**")
            st.caption("Generate the study notes for this file first.")
            st.button("Go to Notes", icon=":material/description:", type="primary", on_click=go_to, args=("Notes",))
        return

    with st.container(key="card_tutor"):
        audio_tutor(
            "Explain to me (Audio)",
            f"notes_{file_id}",
            lambda language: tutor_script_for_notes(notes["markdown"], language),
        )
