"""Quiz History page."""

import pandas as pd
import streamlit as st

from ui.components import page_header


def render():
    page_header("Quiz History", "Every quiz you completed in this session.")
    with st.container(key="card_history"):
        if st.session_state.history:
            st.dataframe(pd.DataFrame(st.session_state.history), hide_index=True, width="stretch")
        else:
            st.markdown("**No quizzes completed yet.**")
            st.caption("Your scores will appear here after you submit a quiz.")
