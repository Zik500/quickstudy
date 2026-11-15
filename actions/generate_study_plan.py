"""Action: make today's study plan (Groq, Gemini as backup)."""

from config import GROQ_MAIN, PLAN_ACTIONS
from services.ai_router import ask_ai_json
from state import chapter_name, days_until_exam, find_notes, get, get_library


def plan_with_groq(language: str) -> list[dict]:
    """Ask for 3-4 study tasks for today. Each task: title, reason, action, chapter."""
    library = get_library()
    history = get("history")
    quizzed = " ".join(row["Chapters"] for row in history)
    chapters = "\n".join(
        f"- {f}: study notes {'ready' if find_notes(f, language) else 'not made yet'}, "
        f"{'quizzed' if chapter_name(f) in quizzed else 'not quizzed yet'}"
        for f in library
    )
    weak = sorted(get("weak_topics").items(), key=lambda item: item[1], reverse=True)[:5]
    weak_text = "\n".join(f"- {topic}: {count} mistakes" for topic, count in weak) or "none yet"
    days = days_until_exam()

    instructions = f"""You are a friendly study coach. Write in {language}.
Reply ONLY with JSON: {{"tasks": [{{"title": "...", "reason": "...", "action": "...", "chapter": "..."}}]}}
Give 3-4 tasks for today. "action" is one of: notes, quiz, audio, revise, ask.
Priorities: weak topics first (action "revise"), then chapters not quizzed yet (action "quiz"),
then chapters without study notes (action "notes"). If the exam is in 7 days or less, focus on
revising and quizzes. "chapter" is one exact file name from the list ("" for revise).
Title: at most 8 words. Reason: one short sentence."""
    content = (
        f"CHAPTERS:\n{chapters}\n\nWEAK TOPICS:\n{weak_text}\n\n"
        f"DAYS UNTIL EXAM: {days if days is not None else 'not set'}\n"
        f"QUIZZES TAKEN: {len(history)}"
    )
    data, _ = ask_ai_json(
        [{"role": "system", "content": instructions}, {"role": "user", "content": content}],
        max_tokens=1500,
        model=GROQ_MAIN,
    )

    tasks = []
    for task in data.get("tasks", []):
        if not isinstance(task, dict) or str(task.get("action", "")).lower() not in PLAN_ACTIONS:
            continue
        tasks.append({
            "title": str(task.get("title", "")).strip(),
            "reason": str(task.get("reason", "")).strip(),
            "action": str(task["action"]).lower(),
            "chapter": task.get("chapter") if task.get("chapter") in library else "",
        })
    if not tasks:
        raise RuntimeError("The study plan came back empty")
    return tasks[:4]
