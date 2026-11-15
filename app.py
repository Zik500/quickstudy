"""QuickStudy: turn PDF lecture notes into study notes and quizzes with AI.

Entry point and router only (like routes/web.php): set up the page, draw the layout,
and show the view for the page chosen in the sidebar. No business logic here.

Run with:  python -m streamlit run app.py
"""

import streamlit as st

from actions.sync_data import sync_user
from state import get, init_state
from ui.layout import current_student_name, load_css, show_sidebar
from views import ask_notes, audio_tutor, history, home, notes, quiz, weak_topics

# Page name (as shown in the sidebar) -> view module with a render() function
ROUTES = {
    "Home": home,
    "Notes": notes,
    "Ask Notes": ask_notes,
    "Quiz": quiz,
    "Audio Tutor": audio_tutor,
    "Weak Topics": weak_topics,
    "History": history,
}


def main():
    st.set_page_config(page_title="QuickStudy", page_icon="📚", initial_sidebar_state="expanded")
    load_css()
    init_state()
    sync_user(current_student_name())  # load the student's saved data from Supabase (if the name changed)
    ROUTES[get("page")].render()
    # The sidebar is drawn last, so it already shows a PDF uploaded on this run
    show_sidebar()


main()
