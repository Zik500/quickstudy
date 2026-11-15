"""Action: keep the student's data in Supabase in sync with st.session_state.

- sync_user(name) loads all saved data when a student types their name.
- The save_... functions are called whenever data changes.
- If Supabase is not configured or fails, the app keeps working with st.session_state only
  ("offline mode"); nothing here ever stops the app.
"""

from datetime import date, datetime

from data import repositories as repo
from data.client import get_client
from state import get, get_library, put, record_result, report_question, reset_user_data

# ---------- Status ----------


def is_online() -> bool:
    """True if a student is signed in by name and Supabase works."""
    return get("db_user_id") is not None and not get("db_offline")


def db_status() -> str:
    """"online", "offline" (Supabase missing or failing) or "no_name" (nobody typed a name yet)."""
    if get_client() is None or get("db_offline"):
        return "offline"
    return "online" if get("db_user_id") is not None else "no_name"


def run_safely(task: str, function, *args):
    """Run one repository function. On any error: log it, switch to offline mode, return None."""
    if not is_online():
        return None
    try:
        return function(*args)
    except Exception as e:
        print(f"[QuickStudy] Supabase {task} failed: {e!r}")
        put("db_offline", True)
        return None


# ---------- Turning database rows into session data (pure functions, easy to test) ----------


def local_time(timestamp: str) -> datetime:
    """A Supabase timestamp ("2026-11-15T12:00:00+00:00") in the computer's local time."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone()


def file_info(row: dict) -> dict:
    """A library_files row as a library entry."""
    pages = row.get("pages") or []
    return {
        "name": row["file_name"],
        "hash": row.get("file_hash") or row["file_name"],
        "pages": pages,
        "text": row.get("text", ""),
        "num_pages": len(pages),
        "outline": row.get("outline"),
        "outline_error": "",
        "text_source": row.get("text_source", "pypdf"),
        "db_id": row["id"],
    }


def build_history(attempts: list[dict], answers: list[dict]) -> list[dict]:
    """Quiz History rows from saved attempts and their answers."""
    by_attempt = {}
    for answer in answers:
        by_attempt.setdefault(answer["attempt_id"], []).append(answer)
    rows = []
    for number, attempt in enumerate(attempts, start=1):
        reported = [f"Q{i + 1}" for i, a in enumerate(by_attempt.get(attempt["id"], [])) if a.get("reported")]
        rows.append({
            "Quiz": number,
            "Type": "Revision" if attempt["label"] == "revision" else "Regular",
            "Chapters": ", ".join(attempt.get("chapters") or []),
            "Difficulty": (attempt.get("settings") or {}).get("difficulty", ""),
            "Score": f"{attempt['score']}/{attempt['total']}",
            "Reported": ", ".join(reported),
            "Time": local_time(attempt["created_at"]).strftime("%d %b, %H:%M"),
        })
    return rows


def build_weak_topics(answers: list[dict]) -> dict:
    """Mistakes per topic: wrong answers that were not reported."""
    weak = {}
    for answer in answers:
        if answer["is_correct"] or answer.get("reported"):
            continue
        key = f"{answer['chapter']} - {answer['topic']}" if answer.get("chapter") else answer["topic"]
        weak[key] = weak.get(key, 0) + 1
    return weak


def build_activity(files: list[dict], attempts: list[dict]) -> list[dict]:
    """Activity entries (for the study streak and "Continue where you left off")."""
    events = [("upload", "", row["file_name"], row["created_at"]) for row in files]
    events += [("quiz", f"{a['score']}/{a['total']}", ", ".join(a.get("chapters") or []), a["created_at"])
               for a in attempts]
    activity = []
    for kind, detail, file, created in sorted(events, key=lambda event: event[3]):
        moment = local_time(created)
        activity.append({"kind": kind, "detail": detail, "file": file,
                         "date": moment.date().isoformat(), "time": moment.strftime("%H:%M")})
    return activity[-50:]


# ---------- Loading ----------


def sync_user(name: str):
    """Called on every run. When the name in the sidebar changes, load that student's data."""
    name = (name or "").strip()
    if name == get("db_user_name"):
        return
    if get("db_user_name"):
        reset_user_data()  # switching from another student: start with an empty session
    put("db_user_name", name)
    put("db_user_id", None)
    put("db_offline", False)
    if not name:
        return
    if get_client() is None:
        put("db_offline", True)
        return
    try:
        user = repo.get_or_create_user(name)
        put("db_user_id", user["id"])
        load_user_data(user)
    except Exception as e:
        print(f"[QuickStudy] Supabase loading failed: {e!r}")
        put("db_user_id", None)
        put("db_offline", True)


def load_user_data(user: dict):
    """Fill st.session_state with everything saved for this student."""
    library = get_library()
    files = repo.load_library_files(user["id"])
    for row in files:
        if row["file_name"] in library:
            library[row["file_name"]]["db_id"] = row["id"]
        else:
            info = file_info(row)
            library[info["name"]] = info
            put(f"pages_{info['name']}", (1, max(info["num_pages"], 1)))

    # PDFs uploaded before the name was typed are saved now
    for file_id, info in library.items():
        if "db_id" not in info:
            info["db_id"] = repo.save_library_file(user["id"], info)

    # Saved study notes, so the AI is not asked again
    names_by_id = {info["db_id"]: file_id for file_id, info in library.items()}
    notes_cache = get("notes_cache")
    for row in repo.load_study_notes(list(names_by_id)):
        file_id = names_by_id.get(row["file_id"])
        if file_id:
            notes_cache[f"{file_id}|{row['language']}"] = {
                "markdown": row["content"], "source": row["generated_by"], "error": None,
            }

    attempts, answers = repo.load_history(user["id"])
    put("history", build_history(attempts, answers))
    put("weak_topics", build_weak_topics(answers))
    put("quiz_number", len(attempts))
    put("activity", build_activity(files, attempts) + get("activity"))

    if user.get("exam_date"):
        put("exam_date", date.fromisoformat(user["exam_date"]))
    plan = repo.load_study_plan(user["id"], date.today().isoformat())
    if plan:
        put("study_plan", {"date": plan["plan_date"], "id": 1, "tasks": plan["tasks"]})


# ---------- Saving (called whenever data changes) ----------


def save_file(file_id: str):
    """Save an uploaded PDF (with its outline)."""
    info = get_library()[file_id]
    db_id = run_safely("save file", repo.save_library_file, get("db_user_id"), info)
    if db_id:
        info["db_id"] = db_id


def save_outline(file_id: str):
    """Save a chapter outline (after "Try again" on the Notes page)."""
    info = get_library().get(file_id, {})
    if info.get("db_id") and info.get("outline"):
        run_safely("save outline", repo.save_outline, info["db_id"], info["outline"])


def delete_file(info: dict):
    """Delete a removed PDF (and its notes) from the database."""
    if info.get("db_id"):
        run_safely("delete file", repo.delete_library_file, info["db_id"])


def save_notes(file_id: str, language: str, notes: dict):
    """Save AI study notes. Offline sumy summaries are not saved, so the AI is tried again later."""
    info = get_library().get(file_id, {})
    if info.get("db_id") and not notes.get("error"):
        run_safely("save notes", repo.save_study_notes, info["db_id"], language, notes["markdown"], notes["source"])


def submit_quiz(questions: list[dict], answers: list[int]):
    """Record a submitted quiz (weak topics + history) and save it with all answers."""
    record_result(questions, answers)
    rows = [{
        "question": q["question"],
        "topic": q["topic"],
        "chapter": q.get("chapter", ""),
        "user_answer": q["options"][a],
        "correct_answer": q["answer"],
        "is_correct": a == q["correct_index"],
    } for q, a in zip(questions, answers)]
    settings = {"difficulty": get("quiz_level"), "count": len(questions), "source": get("quiz_source"),
                "generated_by": get("quiz_generator")}
    label = "revision" if get("quiz_type") == "Revision" else "normal"
    score = sum(row["is_correct"] for row in rows)
    saved = run_safely("save quiz", repo.save_quiz_attempt, get("db_user_id"), get("quiz_chapters"), settings,
                       label, score, len(rows), rows)
    if saved:
        get("db_answer_ids")[get("quiz_number")] = saved[1]


def report(index: int):
    """"⚑ Report question" (button callback): update the session and the database."""
    report_question(index)
    answer_ids = get("db_answer_ids").get(get("quiz_number"))
    if answer_ids and index < len(answer_ids):
        run_safely("report question", repo.mark_question_reported, answer_ids[index])


def save_exam_date():
    """Save the exam date (date input callback)."""
    run_safely("save exam date", repo.save_exam_date, get("db_user_id"), get("exam_date"))


def save_plan(plan: dict):
    """Save today's study plan."""
    run_safely("save study plan", repo.save_study_plan, get("db_user_id"), plan["date"], plan["tasks"])
