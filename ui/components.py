"""Reusable UI pieces: selectors, cards, chat bubbles, upload card, audio tutor."""

import html
import json

import streamlit as st

from actions.manage_library import add_to_library
from actions.revise_weak_topics import revise_weak_topics, revision_problem
from config import LANGUAGES
from services.tts import text_to_speech
from state import go_to
from utils.text import friendly_error, page_count, strip_markdown


def audio_tutor(button_label: str, key: str, write_script, auto: bool = False):
    """Show an Audio Tutor button. On click, create the script and audio once
    (per language), then show the audio player with the script to read along.

    write_script is a function that takes the language name and returns text.
    auto=True skips the button (used when another "Listen" button was already clicked).
    """
    language = st.session_state.tutor_language
    cache_key = f"{key}_{language}"
    saved = st.session_state.tutor_cache.get(cache_key)

    if saved is None:
        if not auto and not st.button(f"🎧 {button_label}", key=f"tutor_{cache_key}"):
            return
        with st.spinner(f"Your AI tutor is preparing an explanation in {language}..."):
            try:
                script = strip_markdown(write_script(language))
                audio = text_to_speech(script, LANGUAGES[language])
            except Exception as e:
                st.error(f"The Audio Tutor is not available right now. {friendly_error(e)}")
                return
        saved = {"script": script, "audio": audio}
        st.session_state.tutor_cache[cache_key] = saved

    st.audio(saved["audio"], format="audio/mp3")
    with st.expander(f"📄 Read along ({language})", expanded=True):
        st.write(saved["script"])


def page_header(title: str, subtitle: str):
    st.markdown(
        f'<div class="qs-page-title">{title}</div><div class="qs-page-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def language_selector(where: str):
    """Language picker. The choice is saved in st.session_state.tutor_language
    so every page remembers it."""
    key = f"language_{where}"

    def save_choice():
        st.session_state.tutor_language = st.session_state[key]

    st.selectbox(
        "Language",
        list(LANGUAGES),
        index=list(LANGUAGES).index(st.session_state.tutor_language),
        key=key,
        on_change=save_choice,
        label_visibility="collapsed",
    )


def notes_selector():
    """'Choose notes' selectbox, shared by the Notes and Audio Tutor pages."""
    library = st.session_state.library
    if st.session_state.get("current_file") not in library:
        st.session_state.current_file = next(reversed(library))  # newest file
    st.selectbox(
        "Choose notes",
        list(library),
        key="current_file",
        persist_state="session",
    )


def require_library() -> bool:
    """Return True if at least one PDF is uploaded; otherwise show a hint card."""
    if st.session_state.library:
        return True
    with st.container(key="card_empty"):
        st.markdown("**Upload a PDF on the Notes page first.**")
        st.caption("Your uploaded PDFs appear in My Notes in the sidebar.")
        st.button("Go to Notes", icon=":material/description:", type="primary", on_click=go_to, args=("Notes",))
    return False


def upload_card(where: str):
    """Drag & drop area for PDFs. Every new file is added to the library."""
    files = st.file_uploader(
        "Drag and drop your lecture notes (PDF)",
        type="pdf",
        accept_multiple_files=True,
        key=f"uploader_{where}_{st.session_state.uploader_round}",
    )
    for uploaded in files or []:
        # Only add each uploaded file once (the uploader keeps it on every rerun)
        upload_id = getattr(uploaded, "file_id", uploaded.name)
        if upload_id not in st.session_state.seen_uploads:
            st.session_state.seen_uploads.append(upload_id)
            with st.spinner(f"Reading {uploaded.name} and making an outline..."):
                add_to_library(uploaded)
    if st.session_state.upload_error:
        st.error(st.session_state.upload_error)


def chapter_list():
    """List of uploaded chapters with page count and outline status."""
    library = st.session_state.library
    if not library:
        st.caption("No chapters yet. Each PDF you upload becomes one chapter.")
        return
    for file_id, info in library.items():
        status = "outline ready" if info.get("outline") else "no outline yet"
        if info.get("text_source") == "Gemini Vision":
            status += " · Text extracted by: Gemini Vision"
        st.markdown(
            f"📄 **{html.escape(file_id)}** "
            f"<span style='color:#6B7280;font-size:0.85rem'>· {page_count(info)} · {status}</span>",
            unsafe_allow_html=True,
        )


def user_bubble(text: str):
    """Show a student message as a purple bubble on the right."""
    safe = html.escape(text).replace("\n", "<br>")
    st.markdown(f'<div class="qs-user-row"><div class="qs-user-bubble">{safe}</div></div>', unsafe_allow_html=True)


def copy_button(text: str, index: int):
    """A small 'Copy' button that copies the answer to the clipboard (needs JavaScript)."""
    js_text = json.dumps(text).replace("</", "<\\/")  # safe inside <script>
    st.html(
        f"""
<button id="copy-{index}" type="button"
  style="border:none;background:none;color:#6B7280;font-size:0.8rem;cursor:pointer;
         padding:0.3rem 0.4rem;font-family:inherit;">📋 Copy</button>
<script>
  (function () {{
    const button = document.getElementById("copy-{index}");
    button.onclick = function () {{
      navigator.clipboard.writeText({js_text}).then(function () {{
        button.textContent = "✓ Copied";
        setTimeout(function () {{ button.textContent = "📋 Copy"; }}, 1500);
      }});
    }};
  }})();
</script>
""",
        width="content",
        unsafe_allow_javascript=True,
    )


def thinking_indicator():
    """Show 'QuickStudy is thinking...' with blinking dots."""
    st.markdown(
        '<div class="qs-typing">QuickStudy is thinking<span>.</span><span>.</span><span>.</span></div>',
        unsafe_allow_html=True,
    )


def run_quiz_with_status(make_quiz) -> bool:
    """Run a quiz action inside a step-by-step status box with a timer.

    make_quiz(progress) is an action that reports each step with progress(message)
    and returns the seconds it took. Returns True if the quiz was made.
    """
    with st.status("Creating your quiz...", expanded=True) as status:
        try:
            seconds = make_quiz(st.write)
        except Exception as e:
            status.update(label="Could not create the quiz", state="error", expanded=True)
            st.error(friendly_error(e))
            return False
        st.write("Done")
        status.update(label=f"Quiz ready in {seconds:.1f} seconds", state="complete", expanded=False)
    return True


def start_revision_quiz(topics: list[str]):
    """Make a 5-question revision quiz on these topics and open the Quiz page.
    It reuses the normal quiz UI and is saved to history as "Revision"."""
    problem = revision_problem()
    if problem:
        st.error(problem)
        return
    if run_quiz_with_status(lambda progress: revise_weak_topics(topics, progress)):
        st.session_state.revision_ready = True
        go_to("Quiz")
        st.rerun()


def topic_tags(question: dict) -> str:
    """HTML: the short topic name as a purple pill + the chapter name as a small grey label."""
    chapter = question.get("chapter", "")
    label = f'<span class="qs-chapter-label">{html.escape(chapter)}</span>' if chapter else ""
    return f'<span class="qs-topic-pill">{html.escape(question["topic"])}</span>{label}'


def topic_pills(topics: list[str]) -> str:
    """HTML: several short topic names as purple pills."""
    return "".join(f'<span class="qs-topic-pill">{html.escape(t)}</span>' for t in topics)


def status_badge(correct: bool) -> str:
    """HTML: green "✓ Correct" or red "✗ Wrong" badge."""
    return ('<span class="qs-badge qs-badge-ok">✓ Correct</span>' if correct
            else '<span class="qs-badge qs-badge-bad">✗ Wrong</span>')


def answer_pill(text: str, correct: bool) -> str:
    """HTML: green "✓ Correct answer: ..." or red "✗ Your answer: ..." pill."""
    if correct:
        return f'<div class="qs-pill qs-pill-right">✓ Correct answer: {html.escape(text)}</div>'
    return f'<div class="qs-pill qs-pill-wrong">✗ Your answer: {html.escape(text)}</div>'


def stat_tile(label: str, value: str, note: str) -> str:
    """HTML for one small stat card."""
    return (f'<div class="qs-stat"><div class="qs-stat-label">{label}</div>'
            f'<div class="qs-stat-value">{value}</div><div class="qs-stat-note">{note}</div></div>')
