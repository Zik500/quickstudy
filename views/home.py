"""Home page: the Study Dashboard."""

from datetime import date
import html

import streamlit as st

from actions.generate_study_plan import plan_with_groq
from actions.sync_data import save_exam_date, save_plan
from config import PLAN_ACTIONS, QUICK_ACTIONS
from state import average_score, chapter_name, days_until_exam, go_to, study_streak
from ui.components import start_revision_quiz, stat_tile
from ui.layout import current_student_name, hero, remember_name
from utils.text import friendly_error, slug


def open_task(action: str, chapter: str):
    """Open the right section with the right chapter selected (button callback)."""
    if chapter in st.session_state.library:
        if action in ("notes", "audio"):
            st.session_state.current_file = chapter
        elif action == "quiz":
            st.session_state.quiz_files = [chapter]
        elif action == "ask":
            st.session_state.chat_files = [chapter]
    go_to(PLAN_ACTIONS[action][2])


def home_subtitle() -> str:
    """A short message based on the student's data."""
    weak = len(st.session_state.weak_topics)
    if not st.session_state.library:
        return "Upload your first chapter to get started."
    if weak:
        return f"You have {weak} weak topic{'s' if weak != 1 else ''}. Let's fix them today."
    if st.session_state.history:
        return "Great job! No weak topics right now."
    return "Take your first quiz to see how you are doing."


def show_stats():
    """Stats row: Chapters, Quizzes taken, Average score, Study streak."""
    average = average_score()
    streak = study_streak()
    tiles = [
        ("Chapters", str(len(st.session_state.library)), "in My Notes"),
        ("Quizzes taken", str(len(st.session_state.history)), "this session"),
        ("Average score", f"{average}%" if average is not None else "–", "across all quizzes"),
        ("Study streak", f"🔥 {streak}", f"day{'s' if streak != 1 else ''} in a row"),
    ]
    for column, tile in zip(st.columns(4), tiles):
        column.markdown(stat_tile(*tile), unsafe_allow_html=True)


def show_study_plan():
    """AI Study Plan for Today: exam date, tasks as a checklist, cached for the day."""
    plan = st.session_state.study_plan
    today = date.today().isoformat()
    has_plan = plan is not None and plan["date"] == today

    with st.container(key="card_plan"):
        st.markdown("**✨ AI Study Plan for Today**")
        date_col, info_col = st.columns([1, 1.6], vertical_alignment="bottom")
        with date_col:
            st.date_input("Exam date", value=None, key="exam_date", persist_state="session", format="DD/MM/YYYY",
                          on_change=save_exam_date)
        with info_col:
            days = days_until_exam()
            if days is None:
                st.caption("Set your exam date to get a plan that fits your time.")
            elif days > 0:
                st.markdown(f"📅 **Exam in {days} day{'s' if days != 1 else ''}**")
            elif days == 0:
                st.markdown("📅 **Your exam is today. Good luck!**")
            else:
                st.caption("This exam date has passed. Choose your next exam date.")

        if has_plan:
            for i, task in enumerate(plan["tasks"]):
                with st.container(key=f"task_{plan['id']}_{i}"):
                    check_col, button_col = st.columns([4, 1.3], vertical_alignment="center")
                    with check_col:
                        st.checkbox(f"**{task['title']}**", key=f"plan_done_{plan['id']}_{i}", persist_state="session")
                        chapter = f" · {chapter_name(task['chapter'])}" if task["chapter"] else ""
                        st.caption(task["reason"] + chapter)
                    with button_col:
                        label, icon, _ = PLAN_ACTIONS[task["action"]]
                        st.button(label, icon=icon, key=f"plan_open_{plan['id']}_{i}", width="stretch",
                                  on_click=open_task, args=(task["action"], task["chapter"]))
            make_plan = st.button("Regenerate", icon=":material/refresh:", type="tertiary", key="plan_regenerate")
        else:
            st.caption("Get 3-4 tasks for today based on your weak topics, your chapters and your exam date.")
            make_plan = st.button("Generate today's plan", type="primary", icon=":material/auto_awesome:",
                                  key="plan_generate")

        if make_plan:
            with st.spinner("Planning your day..."):
                try:
                    tasks = plan_with_groq(st.session_state.tutor_language)
                except Exception as e:
                    st.error(f"Could not make a study plan. {friendly_error(e)}")
                    tasks = None
            if tasks:
                # A new id gives the new plan fresh (unticked) checkboxes
                new_id = plan["id"] + 1 if plan else 1
                st.session_state.study_plan = {"date": today, "id": new_id, "tasks": tasks}
                save_plan(st.session_state.study_plan)
                st.rerun()


def show_continue_card():
    """Continue where you left off: the last quiz, notes or chat."""
    recent = [a for a in st.session_state.activity if a["kind"] in ("quiz", "notes", "ask")]
    with st.container(key="card_continue"):
        st.markdown("**Continue where you left off**")
        if not recent:
            st.caption("Your last quiz, notes or question will appear here.")
            return
        last = recent[-1]
        if last["kind"] == "quiz":
            st.markdown(f"📝 Quiz on **{html.escape(last['file'])}**")
            st.caption(f"You scored {last['detail']} at {last['time']}")
            st.button("Review mistakes", icon=":material/fact_check:", on_click=go_to, args=("Quiz",),
                      key="continue_quiz")
        elif last["kind"] == "notes" and last["file"] in st.session_state.library:
            st.markdown(f"📄 Study notes for **{html.escape(chapter_name(last['file']))}**")
            st.caption(f"Last viewed at {last['time']}")
            st.button("Open notes", icon=":material/description:", on_click=open_task, args=("notes", last["file"]),
                      key="continue_notes")
        else:
            st.markdown(f"💬 You asked about **{html.escape(last['file'] or 'your notes')}**")
            st.caption(f"At {last['time']}")
            st.button("Continue chatting", icon=":material/forum:", on_click=go_to, args=("Ask Notes",),
                      key="continue_ask")


def show_weakest_card():
    """Weakest topic in a purple card with a one-click revision quiz."""
    weak = st.session_state.weak_topics
    if not weak:
        with st.container(key="card_weakest_none"):
            st.markdown("**Weakest topic**")
            st.caption("No weak topics yet. Take a quiz and we will find them for you.")
        return
    topic, count = max(weak.items(), key=lambda item: item[1])
    with st.container(key="card_alert_home"):
        st.markdown("**Weakest topic**")
        st.markdown(f"🎯 {html.escape(topic)}")
        st.caption(f"{count} mistake{'s' if count != 1 else ''} so far")
        if st.button("Revise now", type="primary", icon=":material/autorenew:", key="home_revise"):
            start_revision_quiz([topic])


def show_quick_actions():
    st.markdown('<div class="qs-label">Get started</div>', unsafe_allow_html=True)
    for column, (label, icon, page) in zip(st.columns(4), QUICK_ACTIONS):
        disabled = False
        if page == "Weak Topics":
            if not st.session_state.history:
                label += "  \n:gray[Take a quiz first]"
                disabled = True
            else:
                label += f" :violet-badge[{len(st.session_state.weak_topics)}]"
        with column:
            st.button(
                label,
                icon=icon,
                key=f"action_{slug(page)}",
                width="stretch",
                disabled=disabled,
                on_click=go_to,
                args=(page,),
            )


def show_welcome_card():
    """Ask for the student's name (their saved data is loaded as soon as they type it)."""
    with st.container(key="card_welcome"):
        st.markdown("**👋 Welcome! What's your name?**")
        st.caption("QuickStudy saves your notes, quizzes and study plan under your name.")
        st.text_input(
            "Your name",
            key="welcome_name",
            placeholder="Type your name and press Enter",
            label_visibility="collapsed",
            on_change=lambda: remember_name(st.session_state.welcome_name),
        )


def render():
    hero(home_subtitle())
    if not current_student_name():
        show_welcome_card()

    # Empty state: nothing uploaded yet
    if not st.session_state.library:
        with st.container(key="card_start"):
            st.markdown("**Start by uploading your first chapter** 📚")
            st.caption("Upload your lecture notes (PDF) on the Notes page. QuickStudy then makes an outline, "
                       "study notes, quizzes and a daily study plan for you.")
            st.button("Upload on the Notes page", icon=":material/upload_file:", type="primary",
                      on_click=go_to, args=("Notes",), key="home_start")
        show_quick_actions()
        return

    show_stats()
    show_study_plan()
    left, right = st.columns(2)
    with left:
        show_continue_card()
    with right:
        show_weakest_card()
    show_quick_actions()
