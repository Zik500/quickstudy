"""Tests for turning Supabase rows into session data (actions/sync_data.py). No database needed."""

from actions.sync_data import build_activity, build_history, build_weak_topics, file_info

ATTEMPTS = [
    {"id": 7, "label": "normal", "chapters": ["Chapter 1"], "settings": {"difficulty": "Hard"},
     "score": 1, "total": 3, "created_at": "2026-11-14T08:00:00+00:00"},
    {"id": 9, "label": "revision", "chapters": ["Chapter 1", "Chapter 2"], "settings": {"difficulty": "Easy"},
     "score": 2, "total": 2, "created_at": "2026-11-15T09:30:00+00:00"},
]
ANSWERS = [
    {"attempt_id": 7, "topic": "Defect Rejection Ratio", "chapter": "Chapter 1", "is_correct": False, "reported": False},
    {"attempt_id": 7, "topic": "Fault vs Failure", "chapter": "Chapter 1", "is_correct": False, "reported": True},
    {"attempt_id": 7, "topic": "Test Levels", "chapter": "Chapter 1", "is_correct": True, "reported": False},
    {"attempt_id": 9, "topic": "Defect Rejection Ratio", "chapter": "Chapter 1", "is_correct": True, "reported": False},
    {"attempt_id": 9, "topic": "Reviews", "chapter": "", "is_correct": True, "reported": False},
]


def test_history_rows():
    rows = build_history(ATTEMPTS, ANSWERS)
    assert [r["Quiz"] for r in rows] == [1, 2]
    assert rows[0]["Type"] == "Regular" and rows[1]["Type"] == "Revision"
    assert rows[0]["Score"] == "1/3" and rows[0]["Difficulty"] == "Hard"
    assert rows[0]["Reported"] == "Q2"  # the second question of quiz 1 was reported
    assert rows[1]["Chapters"] == "Chapter 1, Chapter 2"


def test_weak_topics_skip_correct_and_reported_answers():
    assert build_weak_topics(ANSWERS) == {"Chapter 1 - Defect Rejection Ratio": 1}


def test_activity_is_sorted_by_time():
    files = [{"file_name": "Chapter 1.pdf", "created_at": "2026-11-13T10:00:00+00:00"}]
    activity = build_activity(files, ATTEMPTS)
    assert [a["kind"] for a in activity] == ["upload", "quiz", "quiz"]
    assert activity[-1]["detail"] == "2/2"


def test_file_info_from_a_database_row():
    row = {"id": 3, "file_name": "Chapter 1.pdf", "file_hash": "abc", "pages": ["p1", "p2"], "text": "p1\np2",
           "outline": [{"title": "Intro", "description": "Start"}], "text_source": "Gemini Vision"}
    info = file_info(row)
    assert info["num_pages"] == 2 and info["db_id"] == 3 and info["text_source"] == "Gemini Vision"
