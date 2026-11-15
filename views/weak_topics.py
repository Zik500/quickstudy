"""Weak Topics page: mistakes per topic and revision quizzes."""

import pandas as pd
import streamlit as st

from ui.components import page_header, start_revision_quiz


def render():
    page_header("Weak Topics", "Topics you got wrong across all quizzes in this session.")
    weak_topics = st.session_state.weak_topics
    if not weak_topics:
        with st.container(key="card_weak_empty"):
            st.markdown("**Nothing here yet.**")
            st.caption("Take a quiz first. Topics you get wrong will appear here.")
        return

    table = pd.DataFrame(
        sorted(weak_topics.items(), key=lambda item: item[1], reverse=True),
        columns=["Topic", "Mistakes"],
    )
    weakest = table["Topic"].head(3).tolist()
    top_topic, top_count = table.iloc[0]

    # Highlighted card: the weakest topic + one-click revision of the top 3
    with st.container(key="card_alert_weakest"):
        st.markdown(f"**Your weakest topic:** {top_topic} ({top_count} {'mistake' if top_count == 1 else 'mistakes'})")
        st.caption(f"The revision quiz focuses on: {', '.join(weakest)}")
        if st.button("Revise Weak Topics", type="primary", icon=":material/autorenew:", key="revise_weak"):
            start_revision_quiz(weakest)

    with st.container(key="card_weak"):
        st.markdown("**Mistakes per topic**")
        st.bar_chart(table, x="Topic", y="Mistakes", horizontal=True, sort="-Mistakes", color="#7C3AED")

        # One row per topic with its own "Practice" button
        for i, row in table.iterrows():
            name_col, count_col, button_col = st.columns([3, 1.4, 1.2], vertical_alignment="center")
            name_col.markdown(row["Topic"])
            count_col.caption(f"{row['Mistakes']} {'mistake' if row['Mistakes'] == 1 else 'mistakes'}")
            if button_col.button("Practice", key=f"practice_{i}", icon=":material/play_arrow:", width="stretch"):
                start_revision_quiz([row["Topic"]])
