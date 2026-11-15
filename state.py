"""All st.session_state keys in one place: defaults, library queries, quiz results and activity."""

from datetime import date, datetime, timedelta

import streamlit as st

from config import QUIZ_SOURCES


def get(key: str, default=None):
    """Read one session value."""
    return st.session_state.get(key, default)


def put(key: str, value):
    """Save one session value."""
    st.session_state[key] = value


def get_library() -> dict:
    """The uploaded PDFs: {file name: {"name", "hash", "pages", "text", "num_pages", "outline"}}."""
    return st.session_state.library


def init_state():
    """Create all session values on the first run."""
    defaults = {
        "page": "Home",          # which section is open
        "tutor_language": "English",
        "library": {},           # uploaded PDFs (see get_library)
        "upload_error": "",
        "notes_cache": {},       # "<file_id>|<language>" -> {"markdown", "source", "error"}
        "quiz": None,            # list of question dicts
        "quiz_text": "",         # chapter text the current quiz was made from
        "quiz_chapters": [],     # chapter names of the current quiz
        "quiz_number": 0,        # counts quizzes in this session
        "quiz_type": "",         # "Regular" or "Revision"
        "quiz_level": "",        # difficulty of the current quiz
        "submitted": False,
        "answers": [],
        "explanations": {},      # question index -> {"explanation", "quote", "generated_by"} ("Explain more")
        "reported": [],          # question indexes of the current quiz that the student reported
        "tutor_cache": {},       # "<item>_<language>" -> {"script", "audio"}
        "weak_topics": {},       # topic -> number of mistakes
        "history": [],           # past quiz results
        "chat": [],              # Ask Notes messages
        "chat_audio": {},        # message index -> MP3 bytes
        "seen_uploads": [],      # uploader files already added to the library
        "activity": [],          # what the student did: {"kind", "detail", "file", "date", "time"}
        "study_plan": None,      # today's AI study plan: {"date", "id", "tasks"}
        "uploader_round": 0,     # changing this resets the file uploaders
        # Widget values (kept across pages with persist_state="session")
        "chat_files": [],
        "quiz_files": [],
        "quiz_count": 5,
        "quiz_difficulty": "Medium",
        "quiz_source": QUIZ_SOURCES[0],
        "quiz_cache": {},        # chapters + settings -> {"questions", "generator", "text"}
        "quiz_generator": "",    # which AI wrote the current quiz
        "quiz_seconds": 0.0,     # how long the current quiz took
        # Supabase (data tier)
        "db_user_name": None,    # name the data was loaded for
        "db_user_id": None,      # users.id in Supabase (None = not saving)
        "db_offline": False,     # True if Supabase is missing or failed
        "db_answer_ids": {},     # quiz number -> answer row ids (for "Report question")
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# Everything that belongs to one student (cleared when another name is typed)
USER_DATA_KEYS = [
    "library", "notes_cache", "quiz", "quiz_text", "quiz_chapters", "quiz_number", "quiz_type", "quiz_level",
    "submitted", "answers", "explanations", "reported", "tutor_cache", "weak_topics", "history", "chat",
    "chat_audio", "seen_uploads", "activity", "study_plan", "chat_files", "quiz_files", "quiz_cache",
    "db_answer_ids", "current_file", "exam_date",
]


def reset_user_data():
    """Forget the current student's data (before loading another student's data)."""
    for key in list(st.session_state):
        if key in USER_DATA_KEYS or key.startswith(("pages_", "plan_done_", "play_")):
            del st.session_state[key]
    st.session_state.uploader_round = st.session_state.get("uploader_round", 0) + 1  # empty the uploaders
    init_state()


def go_to(page: str):
    """Open a section (used as a button callback)."""
    st.session_state.page = page


def chapter_name(file_id: str) -> str:
    """The file name without ".pdf", used as the chapter name."""
    return st.session_state.library[file_id]["name"].rsplit(".", 1)[0]


def build_notes_text(file_ids: list[str], max_chars: int, use_page_ranges: bool = False) -> str:
    """Join the chosen chapters into one text, each with a chapter heading.
    The character limit is shared equally between the chapters."""
    if not file_ids:
        return ""
    per_chapter = max_chars // len(file_ids)
    parts = []
    for file_id in file_ids:
        info = st.session_state.library[file_id]
        first, last = 1, info["num_pages"]
        if use_page_ranges:
            first, last = st.session_state.get(f"pages_{file_id}", (first, last))
        text = "\n".join(info["pages"][first - 1:last])
        parts.append(f"=== CHAPTER: {chapter_name(file_id)} (pages {first}-{last}) ===\n{text[:per_chapter]}")
    return "\n\n".join(parts)


def outline_titles(file_ids: list[str]) -> list[str]:
    """All section titles of the chosen chapters (used as clickable options)."""
    titles = []
    for file_id in file_ids:
        for section in st.session_state.library[file_id].get("outline") or []:
            titles.append(section["title"])
    return titles


def outline_text(file_ids: list[str]) -> str:
    """The outlines of the chosen chapters as plain text for the chat prompt."""
    lines = []
    for file_id in file_ids:
        lines.append(f"{chapter_name(file_id)}:")
        for section in st.session_state.library[file_id].get("outline") or []:
            lines.append(f"- {section['title']}: {section['description']}")
    return "\n".join(lines)


def find_notes(file_id: str, language: str):
    """Saved study notes for a chapter: in this language if possible, otherwise any language."""
    cache = st.session_state.notes_cache
    return cache.get(f"{file_id}|{language}") or next(
        (value for key, value in cache.items() if key.startswith(f"{file_id}|")), None
    )


def start_quiz(questions: list[dict], quiz_type: str, chapters: list[str], text: str, level: str,
               generator: str, seconds: float):
    """Save a new quiz and reset the previous answers."""
    st.session_state.quiz = questions
    st.session_state.quiz_generator = generator
    st.session_state.quiz_seconds = seconds
    st.session_state.quiz_text = text
    st.session_state.quiz_chapters = chapters
    st.session_state.quiz_level = level
    st.session_state.quiz_number += 1
    st.session_state.quiz_type = quiz_type
    st.session_state.submitted = False
    st.session_state.answers = []
    st.session_state.explanations = {}
    st.session_state.reported = []


def record_result(questions: list[dict], answers: list[int]):
    """Update the weak topic tracker and quiz history after a submission."""
    score = 0
    for q, answer in zip(questions, answers):
        if answer == q["correct_index"]:
            score += 1
        else:
            topic = q["topic_key"]
            st.session_state.weak_topics[topic] = st.session_state.weak_topics.get(topic, 0) + 1

    st.session_state.history.append({
        "Quiz": st.session_state.quiz_number,
        "Type": st.session_state.quiz_type,
        "Chapters": ", ".join(st.session_state.quiz_chapters),
        "Difficulty": st.session_state.quiz_level,
        "Score": f"{score}/{len(questions)}",
        "Reported": "",
        "Time": datetime.now().strftime("%d %b, %H:%M"),
    })
    log_activity("quiz", f"{score}/{len(questions)}", ", ".join(st.session_state.quiz_chapters))


def report_question(index: int):
    """The student reports question `index` of the current quiz as wrong (button callback).
    It is marked in the history and no longer counts as a weak topic."""
    if index in st.session_state.reported:
        return
    st.session_state.reported.append(index)
    q = st.session_state.quiz[index]

    # A wrong answer to a reported question should not count as a mistake
    answers = st.session_state.answers
    if index < len(answers) and answers[index] != q["correct_index"]:
        weak = st.session_state.weak_topics
        weak[q["topic_key"]] = weak.get(q["topic_key"], 0) - 1
        if weak[q["topic_key"]] <= 0:
            del weak[q["topic_key"]]

    # Mark it in this quiz's history row
    for row in st.session_state.history:
        if row["Quiz"] == st.session_state.quiz_number:
            row["Reported"] = ", ".join(f"Q{i + 1}" for i in sorted(st.session_state.reported))


def start_over():
    """Clear everything, including the uploaded files."""
    next_round = st.session_state.uploader_round + 1
    st.session_state.clear()
    st.session_state.uploader_round = next_round


def log_activity(kind: str, detail: str, file_id: str = ""):
    """Remember what the student did (for the study streak and "Continue where you left off").
    kind is "upload", "notes", "quiz" or "ask"."""
    entry = {"kind": kind, "detail": detail, "file": file_id,
             "date": date.today().isoformat(), "time": datetime.now().strftime("%H:%M")}
    activity = st.session_state.activity
    if activity and kind == "notes" and activity[-1]["kind"] == "notes" and activity[-1]["file"] == file_id:
        activity[-1] = entry  # still viewing the same notes: only update the time
    else:
        activity.append(entry)
    del activity[:-50]  # keep only the last 50 entries


def study_streak() -> int:
    """Number of days in a row with any activity (counting back from today or yesterday)."""
    active_days = {a["date"] for a in st.session_state.activity}
    day = date.today()
    if day.isoformat() not in active_days:
        day -= timedelta(days=1)  # nothing yet today: the streak is still alive from yesterday
    streak = 0
    while day.isoformat() in active_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def average_score():
    """Average quiz score in percent, or None if no quizzes yet."""
    percents = []
    for row in st.session_state.history:
        right, total = row["Score"].split("/")
        percents.append(int(right) / int(total) * 100)
    return round(sum(percents) / len(percents)) if percents else None


def days_until_exam():
    """Days from today until the exam date, or None if no date is set."""
    exam = st.session_state.get("exam_date")
    return (exam - date.today()).days if exam else None
