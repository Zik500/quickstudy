"""Action: write spoken Audio Tutor scripts (fast Groq model, Gemini as backup)."""

from config import GROQ_FAST, MAX_GROQ_CHARS, TUTOR_STYLE
from services.ai_router import ask_ai


def tutor_script_for_notes(notes_text: str, language: str) -> str:
    """Write a ~150-200 word spoken lesson about the study notes."""
    instructions = TUTOR_STYLE.format(language=language) + (
        " Write a script of about 150-200 words. Explain the 3-4 most important "
        "concepts from the notes, use one everyday example or analogy, and end with "
        "one quick question for the student to think about."
    )
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": notes_text[:MAX_GROQ_CHARS]}]
    script, _ = ask_ai(messages, max_tokens=1500, model=GROQ_FAST)
    return script


def tutor_script_for_mistake(q: dict, chosen: int, explanation: str, language: str) -> str:
    """Turn a wrong-answer explanation into a short spoken explanation (max 80 words)."""
    instructions = TUTOR_STYLE.format(language=language) + (
        " In at most 80 words, gently explain why the student's answer was wrong "
        "and why the correct answer is right. Be encouraging."
    )
    content = (
        f"Question: {q['question']}\n"
        f"Student's answer: {q['options'][chosen]}\n"
        f"Correct answer: {q['answer']}\n"
        f"Explanation: {explanation}"
    )
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": content}]
    script, _ = ask_ai(messages, max_tokens=800, model=GROQ_FAST)
    return script
