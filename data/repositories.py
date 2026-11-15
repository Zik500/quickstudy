"""Repository functions: all reading and writing of QuickStudy data in Supabase
(like Models/Repositories in Laravel). Only database code here.

Every function raises an exception if Supabase fails; the caller (actions/sync_data.py)
then switches the app to offline mode.
"""

from data.client import db

# ---------- Users ----------


def get_or_create_user(name: str) -> dict:
    """The user row for this name (created on first use)."""
    rows = db().table("users").select("*").eq("name", name).execute().data
    if rows:
        return rows[0]
    return db().table("users").insert({"name": name}).execute().data[0]


def save_exam_date(user_id: int, exam_date):
    """Save the exam date (a date, or None to clear it)."""
    value = exam_date.isoformat() if exam_date else None
    db().table("users").update({"exam_date": value}).eq("id", user_id).execute()


# ---------- Library files (one PDF = one chapter) ----------


def save_library_file(user_id: int, info: dict) -> int:
    """Save (or replace) an uploaded PDF. Returns its database id."""
    row = {
        "user_id": user_id,
        "file_name": info["name"],
        "file_hash": info.get("hash"),
        "pages": info["pages"],
        "text": info["text"],
        "text_source": info.get("text_source", "pypdf"),
        "outline": info.get("outline"),
    }
    saved = db().table("library_files").upsert(row, on_conflict="user_id,file_name").execute().data
    return saved[0]["id"]


def save_outline(file_db_id: int, outline: list):
    """Save the chapter outline of a file."""
    db().table("library_files").update({"outline": outline}).eq("id", file_db_id).execute()


def load_library_files(user_id: int) -> list[dict]:
    """All uploaded PDFs of a user, oldest first."""
    return db().table("library_files").select("*").eq("user_id", user_id).order("id").execute().data


def delete_library_file(file_db_id: int):
    """Delete a PDF (its study notes are deleted too, by "on delete cascade")."""
    db().table("library_files").delete().eq("id", file_db_id).execute()


# ---------- Study notes ----------


def save_study_notes(file_db_id: int, language: str, content: str, generated_by: str):
    """Save (or replace) the study notes of a file in one language."""
    row = {"file_id": file_db_id, "language": language, "content": content, "generated_by": generated_by}
    db().table("study_notes").upsert(row, on_conflict="file_id,language").execute()


def load_study_notes(file_db_ids: list[int]) -> list[dict]:
    """All study notes of these files."""
    if not file_db_ids:
        return []
    return db().table("study_notes").select("*").in_("file_id", file_db_ids).execute().data


# ---------- Quizzes ----------


def save_quiz_attempt(user_id: int, chapters: list[str], settings: dict, label: str, score: int, total: int,
                      answers: list[dict]) -> tuple[int, list[int]]:
    """Save a submitted quiz and all its answers.
    Returns (attempt id, answer ids in question order)."""
    attempt = db().table("quiz_attempts").insert({
        "user_id": user_id, "chapters": chapters, "settings": settings,
        "label": label, "score": score, "total": total,
    }).execute().data[0]
    rows = [dict(answer, attempt_id=attempt["id"]) for answer in answers]
    saved = db().table("answers").insert(rows).execute().data
    return attempt["id"], [row["id"] for row in sorted(saved, key=lambda r: r["id"])]


def load_history(user_id: int) -> tuple[list[dict], list[dict]]:
    """All quiz attempts of a user (oldest first) and all their answers (in question order)."""
    attempts = db().table("quiz_attempts").select("*").eq("user_id", user_id).order("id").execute().data
    ids = [attempt["id"] for attempt in attempts]
    answers = db().table("answers").select("*").in_("attempt_id", ids).order("id").execute().data if ids else []
    return attempts, answers


def mark_question_reported(answer_id: int):
    """Mark one answered question as reported (it no longer counts as a weak topic)."""
    db().table("answers").update({"reported": True}).eq("id", answer_id).execute()


# ---------- Study plans ----------


def save_study_plan(user_id: int, plan_date: str, tasks: list[dict]):
    """Save (or replace) the study plan of one day (plan_date as "YYYY-MM-DD")."""
    row = {"user_id": user_id, "plan_date": plan_date, "tasks": tasks}
    db().table("study_plans").upsert(row, on_conflict="user_id,plan_date").execute()


def load_study_plan(user_id: int, plan_date: str):
    """The study plan of one day, or None."""
    rows = (db().table("study_plans").select("*").eq("user_id", user_id).eq("plan_date", plan_date)
            .execute().data)
    return rows[0] if rows else None
