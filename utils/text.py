"""Small text helpers: friendly error messages, Markdown stripping, keys and labels."""

import json
import re


def parse_json(raw: str) -> dict:
    """Read a JSON object from an AI reply. strict=False allows line breaks inside strings.
    Raises ValueError if the reply is not a JSON object."""
    data = json.loads(raw, strict=False)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


def trim_text(text: str, max_chars: int) -> str:
    """Keep at most max_chars characters (to stay under an AI text limit)."""
    return text[:max_chars]


# Sentences starting like this show the AI "thinking aloud": they are removed
THINKING_ALOUD = ("wait", "hmm", "hold on", "let me", "let's check", "oops")
# Correction words: the word is removed, but the rest of the sentence (the correction) is kept
CORRECTION_WORDS = ("actually", "on second thought")


def clean_explanation(text: str, max_sentences: int = 3) -> str:
    """Keep only final-answer sentences: drop "Wait...", remove a leading "Actually",
    and limit the length."""
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        lower = sentence.lower().lstrip("*_ ")
        if not sentence or lower.startswith(THINKING_ALOUD):
            continue
        for word in CORRECTION_WORDS:
            if lower.startswith(word):
                sentence = sentence.strip("*_ ")[len(word):].lstrip(" ,")
                sentence = sentence[:1].upper() + sentence[1:]
        if sentence:
            kept.append(sentence)
    return " ".join(kept[:max_sentences]).strip()


def friendly_error(e: Exception) -> str:
    """Turn an API error into a short message a student can understand.
    The full error is only printed in the terminal (for debugging), never shown in the app."""
    print(f"[QuickStudy] error: {e!r}")
    text = str(e)
    if "429" in text or "rate limit" in text.lower() or "quota" in text.lower():
        return "The AI service is busy right now (rate limit reached). Please wait a minute and try again."
    if "_API_KEY is missing" in text:
        return text  # our own message about a missing key in secrets.toml
    return "The AI is busy right now. Please try again in a minute."


def strip_markdown(text: str) -> str:
    """Remove Markdown symbols so they are not read aloud."""
    return re.sub(r"[#*_`>|]", "", text)


def slug(text: str) -> str:
    """Turn a label into a safe widget key, e.g. "Audio Tutor" -> "audio_tutor"."""
    return text.lower().replace(" ", "_")


def page_count(info: dict) -> str:
    """'1 page' or '12 pages'."""
    return f"{info['num_pages']} page{'' if info['num_pages'] == 1 else 's'}"
