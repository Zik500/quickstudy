"""Action: make a revision quiz focused on weak topics."""

from actions.generate_quiz import generate_quiz, no_progress
from services.secrets import get_secret
from state import chapter_name, get_library


def revision_problem():
    """Return a message if a revision quiz cannot be made right now, otherwise None."""
    if not get_library():
        return "Upload a PDF on the Notes page first."
    if not get_secret("GEMINI_API_KEY") and not get_secret("GROQ_API_KEY"):
        return "Add GEMINI_API_KEY or GROQ_API_KEY to .streamlit/secrets.toml to make quizzes."
    return None


def chapters_for_topics(topics: list[str]) -> list[str]:
    """The chapters named in the topics (e.g. "Chapter 1 - ..."); otherwise all chapters."""
    library = get_library()
    joined = " ".join(topics).lower()
    return [f for f in library if chapter_name(f).lower() in joined] or list(library)


def revise_weak_topics(topics: list[str], progress=no_progress) -> float:
    """Make a 5-question revision quiz on the given topics and open it.
    Revision quizzes are never cached, so practising again gives new questions.
    Returns how many seconds it took."""
    return generate_quiz(chapters_for_topics(topics), "Revision", focus_topics=topics, use_cache=False,
                         progress=progress)
