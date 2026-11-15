"""Action: turn a chapter into study notes (Groq, Gemini as backup, sumy offline as last resort)."""

from config import GROQ_MAIN, MAX_GEMINI_CHARS, MAX_GROQ_CHARS
from services.ai_router import ask_ai
from services.fallback_summarizer import notes_with_sumy


def notes_prompt(text: str, language: str) -> list[dict]:
    """Chat messages asking for structured study notes in Markdown."""
    instructions = (
        "You turn lecture notes into clear study notes for students. "
        "Use Markdown: short sections with ### headings, bullet points, "
        "and a final 'Key Terms' section with **term**: definition. "
        f"Use only information from the notes. Write the study notes in {language}."
    )
    return [{"role": "system", "content": instructions}, {"role": "user", "content": text}]


def generate_study_notes(text: str, language: str) -> dict:
    """Make study notes. Returns {"markdown", "source", "error"}.
    If both AIs fail, a simple offline summary (sumy) is used instead."""
    try:
        markdown, label = ask_ai(
            notes_prompt(text[:MAX_GROQ_CHARS], language),
            max_tokens=3000,
            model=GROQ_MAIN,
            backup_messages=notes_prompt(text[:MAX_GEMINI_CHARS], language),
        )
        return {"markdown": markdown, "source": label, "error": None}
    except Exception as e:
        return {"markdown": notes_with_sumy(text), "source": "sumy (fallback)", "error": str(e)}
