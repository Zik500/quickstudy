"""Action: answer an Ask Notes question only from the chosen chapters."""

from config import FOLLOW_UP, GROQ_FAST, MAX_CHAT_MESSAGES, MAX_CHAT_NOTES_CHARS, NOT_COVERED, OVERVIEW, WHICH_PART
from services.ai_router import ask_ai_json
from state import build_notes_text, get, outline_text, outline_titles
from utils.text import friendly_error


def chat_answer(chat_history: list[dict], language: str, file_ids: list[str]) -> dict:
    """Answer the latest question ONLY from the chosen chapters, or ask which part
    to explain when the question is too broad.
    Returns {"type": "answer" or "clarify", "answer", "options", "sources"}."""
    system = f"""You are QuickStudy, a friendly tutor. Always reply in {language}.
Reply ONLY with JSON in this shape:
{{"type": "answer" or "clarify", "answer": "...", "options": ["..."], "sources": ["..."]}}

Rules:
1. Use ONLY the lecture notes below, never general knowledge. If the answer is not in the notes,
   reply with type "answer", answer exactly "{NOT_COVERED[language]}", and empty options and sources.
2. If the question is broad (for example "explain chapter 1", "explain everything",
   "teach me this chapter", "summarise the notes"), do NOT explain yet. Reply with type "clarify",
   answer exactly "{WHICH_PART[language]}", options = the matching section titles copied exactly
   from the CHAPTER OUTLINES below, and empty sources.
3. Otherwise reply with type "answer". Explain like a friendly tutor: simple words, one everyday
   example, a short intro sentence then bullet points, under 200 words unless the student asks for
   more. Do not put quotes in the answer. End the answer with this question on its own line:
   "{FOLLOW_UP[language]}"
   If the student asks for "{OVERVIEW[language]}", give a short overview of all sections.
4. "sources": up to 3 short word-for-word quotes from the notes that support the answer, each
   starting with the chapter name in brackets, e.g. "[Chapter 1] quote".

CHAPTER OUTLINES:
{outline_text(file_ids)}

LECTURE NOTES:
{build_notes_text(file_ids, MAX_CHAT_NOTES_CHARS)}"""

    # Skip error messages, then keep only the most recent messages
    clean = [{"role": m["role"], "content": m["content"]} for m in chat_history if not m.get("error")]
    data, label = ask_ai_json(
        [{"role": "system", "content": system}] + clean[-MAX_CHAT_MESSAGES:], max_tokens=1500, model=GROQ_FAST
    )

    reply_type = "clarify" if data.get("type") == "clarify" else "answer"
    answer = str(data.get("answer", "")).strip()
    options = [str(o).strip() for o in data.get("options", []) if str(o).strip()]
    sources = [str(s).strip() for s in data.get("sources", []) if str(s).strip()]

    if reply_type == "clarify":
        # Always offer the outline sections plus "Quick overview of everything"
        options = (options or outline_titles(file_ids))[:8]
        options.append(OVERVIEW[language])
        answer = answer or WHICH_PART[language]
        sources = []
    return {"type": reply_type, "answer": answer or NOT_COVERED[language], "options": options,
            "sources": sources, "generated_by": label}


def get_answer(history: list[dict]) -> dict:
    """Get an answer and return it as a chat message (or a friendly error message)."""
    language = get("tutor_language")
    try:
        result = chat_answer(history, language, get("chat_files"))
        return {"role": "assistant", "type": result["type"], "content": result["answer"],
                "options": result["options"], "sources": result["sources"],
                "generated_by": result["generated_by"], "language": language, "error": False}
    except Exception as e:
        return {"role": "assistant", "type": "answer", "content": friendly_error(e), "options": [],
                "sources": [], "language": language, "error": True}
