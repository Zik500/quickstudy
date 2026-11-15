"""Action: make a short outline of a chapter (once per file)."""

from actions.sync_data import save_outline
from config import GROQ_MAIN, MAX_OUTLINE_CHARS
from services.ai_router import ask_ai_json
from state import get_library
from utils.text import friendly_error


def make_outline(file_id: str):
    """Ask Groq ONCE for a short outline of a chapter (4-8 sections) and save it
    in the library. If it fails, the Notes page shows a "Try again" button."""
    info = get_library()[file_id]
    instructions = (
        "You make a short outline of lecture notes. Reply ONLY with JSON in this shape: "
        '{"sections": [{"title": "...", "description": "..."}]}. '
        "List the 4-8 main sections or topics in the order they appear. Each title is 2-6 words; "
        "each description is one short line. Use only the notes."
    )
    try:
        data, _ = ask_ai_json(
            [{"role": "system", "content": instructions},
             {"role": "user", "content": info["text"][:MAX_OUTLINE_CHARS]}],
            max_tokens=1200,
            model=GROQ_MAIN,
        )
        sections = data.get("sections", [])
        info["outline"] = [
            {"title": str(s.get("title", "")).strip(), "description": str(s.get("description", "")).strip()}
            for s in sections if isinstance(s, dict) and s.get("title")
        ][:8]
        info["outline_error"] = ""
        save_outline(file_id)  # Supabase (only if the file is already saved)
    except Exception as e:
        info["outline"] = None
        info["outline_error"] = friendly_error(e)
