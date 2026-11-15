"""Action: write a quiz from the chosen chapters (cached per chapters + settings)."""

import json
import time

from actions.generate_notes import generate_study_notes
from actions.schemas import Quiz
from actions.sync_data import save_notes
from config import DIFFICULTY_HINTS, GROQ_MAIN, MAX_GEMINI_CHARS, MAX_GROQ_CHARS, QUIZ_SOURCES, REVISION_QUESTIONS
from services.ai_router import GEMINI_LABEL, ask_ai_json
from state import build_notes_text, chapter_name, find_notes, get, get_library, start_quiz
from utils.text import clean_explanation
from utils.validators import is_valid_question

QUIZ_RULES = """You write multiple-choice quiz questions from lecture notes.
Rules:
- Every question must be answerable from the notes below. Use only facts from the notes.
- For calculations, work the result out step by step internally, then make sure the "answer"
  option exactly matches the correct result (for example 12/40 = 0.3 = 30%).
- Each question has exactly 4 different options. "answer" is copied exactly from "options".
- "topic": a short topic name of 2-5 words (e.g. "Defect Rejection Ratio").
- "chapter": the chapter name from the "=== CHAPTER: ... ===" heading.
- "explanation": 1-2 short sentences with the final reason only. Never think aloud.
- Return only the final JSON."""


def no_progress(message: str):
    """Default progress callback: do nothing."""


def quiz_messages(text: str, focus_topics, count: int, level: str, avoid: list[str] = None) -> list[dict]:
    """Chat messages for the quiz: the rules once, then the chapter text."""
    focus = f"Focus the questions on these weak topics: {', '.join(focus_topics)}.\n" if focus_topics else ""
    avoid_text = ("Do not repeat these questions:\n- " + "\n- ".join(avoid) + "\n") if avoid else ""
    request = (
        f"Write exactly {count} multiple-choice questions.\n"
        f"Difficulty: {DIFFICULTY_HINTS[level]}\n{focus}{avoid_text}\nCHAPTERS:\n{text}"
    )
    return [{"role": "system", "content": QUIZ_RULES}, {"role": "user", "content": request}]


def prepare_question(question: dict) -> dict:
    """Tidy a valid question: trimmed options, correct_index from the answer text,
    a short explanation, and the topic key used by the weak topic tracker."""
    options = [str(o).strip() for o in question["options"]]
    answer = str(question["answer"]).strip()
    chapter = str(question.get("chapter", "")).strip()
    topic = str(question.get("topic", "")).strip() or "General"
    return {
        "question": str(question["question"]).strip(),
        "options": options,
        "answer": answer,
        "correct_index": options.index(answer),
        "topic": topic,
        "chapter": chapter,
        "topic_key": f"{chapter} - {topic}" if chapter else topic,
        "explanation": clean_explanation(str(question.get("explanation", "")), max_sentences=2),
    }


def ask_for_questions(groq_text: str, gemini_text: str, focus_topics, count: int, level: str,
                      avoid: list[str] = None) -> tuple[list[dict], list[dict], str]:
    """One AI request. Returns (valid questions, invalid questions, label of the AI)."""
    quiz, label = ask_ai_json(
        quiz_messages(groq_text, focus_topics, count, level, avoid),
        max_tokens=2000 + 500 * count,
        schema=Quiz,
        model=GROQ_MAIN,
        reasoning_effort="medium",  # more careful thinking = correct answer keys
        backup_messages=quiz_messages(gemini_text, focus_topics, count, level, avoid),
    )
    questions = [q.model_dump() for q in quiz.questions]
    valid = [prepare_question(q) for q in questions if is_valid_question(q)]
    invalid = [q for q in questions if not is_valid_question(q)]
    return valid, invalid, label


def write_quiz(groq_text: str, gemini_text: str, focus_topics, count: int, level: str,
               progress=no_progress) -> tuple[list[dict], str]:
    """Write and check the questions. Questions with repeated options or an answer that is not
    one of the options are regenerated once (one extra request for all of them).
    Returns (questions, label of the AI that wrote them)."""
    questions, invalid, label = ask_for_questions(groq_text, gemini_text, focus_topics, count, level)
    if label == GEMINI_LABEL:
        progress("Groq was busy, so Gemini wrote the quiz instead.")

    missing = count - len(questions)
    if invalid or missing > 0:
        progress(f"Checking answers: rewriting {max(missing, len(invalid))} question(s)...")
        try:
            extra, _, _ = ask_for_questions(groq_text, gemini_text, focus_topics, max(missing, 1), level,
                                            avoid=[q["question"] for q in questions])
            questions += extra
        except Exception as e:
            print(f"[QuickStudy] could not rewrite questions: {e!r}")

    if not questions:
        raise RuntimeError("The AI did not return any valid questions")
    return questions[:count], label


def quiz_source_text(file_ids: list[str], source: str, max_chars: int, progress=no_progress) -> str:
    """The text a quiz is written from: the study notes (short = fast) or the PDF pages."""
    if source == QUIZ_SOURCES[1]:
        return build_notes_text(file_ids, max_chars, use_page_ranges=True)

    language = get("tutor_language")
    parts = []
    for file_id in file_ids:
        notes = find_notes(file_id, language)
        if notes is None:
            # No study notes yet: make them first and save them for the Notes page too
            progress(f"Writing study notes for {chapter_name(file_id)} first...")
            notes = generate_study_notes(get_library()[file_id]["text"], language)
            get("notes_cache")[f"{file_id}|{language}"] = notes
            save_notes(file_id, language, notes)
        parts.append(f"=== CHAPTER: {chapter_name(file_id)} ===\n{notes['markdown'][:max_chars // len(file_ids)]}")
    return "\n\n".join(parts)


def generate_quiz(file_ids: list[str], quiz_type: str, focus_topics=None, use_cache: bool = True,
                  progress=no_progress) -> float:
    """Make a quiz from the chosen chapters and open it (saved in session state).

    Quizzes are cached per chapters + settings. progress(message) is called for each step.
    Returns how many seconds it took. Raises an exception if no AI could write the quiz.
    """
    source = get("quiz_source")
    count = get("quiz_count") if quiz_type == "Regular" else REVISION_QUESTIONS
    level = get("quiz_difficulty")
    ranges = [get(f"pages_{f}") for f in file_ids] if source == QUIZ_SOURCES[1] else []
    cache_key = json.dumps([file_ids, ranges, count, level, source, focus_topics or []])
    cache = get("quiz_cache")

    start = time.time()
    if use_cache and cache_key in cache:
        progress("Found a saved quiz with the same chapters and settings.")
    else:
        progress("Reading notes...")
        groq_text = quiz_source_text(file_ids, source, MAX_GROQ_CHARS, progress)
        gemini_text = quiz_source_text(file_ids, source, MAX_GEMINI_CHARS)  # longer text for the backup
        progress("Writing questions...")
        questions, generator = write_quiz(groq_text, gemini_text, focus_topics, count, level, progress)
        cache[cache_key] = {"questions": questions, "generator": generator, "text": gemini_text}
    seconds = time.time() - start

    saved = cache[cache_key]
    start_quiz(saved["questions"], quiz_type, [chapter_name(f) for f in file_ids], saved["text"], level,
               saved["generator"], seconds)
    return seconds
