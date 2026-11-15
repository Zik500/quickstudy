"""Groq API client (chat completions). Groq is the primary AI of QuickStudy."""

import groq

from config import GROQ_MAIN, GROQ_TIMEOUT_SECONDS
from services.secrets import get_secret


def groq_chat(messages: list[dict], max_tokens: int, json_mode: bool = False,
              model: str = GROQ_MAIN, reasoning_effort: str = "low") -> str:
    """Send chat messages to Groq and return the text reply.

    json_mode=True asks for a JSON object. reasoning_effort ("low", "medium", "high") controls
    how much the model thinks before answering. No automatic retries: if Groq fails or takes
    longer than GROQ_TIMEOUT_SECONDS, the AI router asks Gemini instead.
    """
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing in .streamlit/secrets.toml")

    client = groq.Groq(api_key=api_key, timeout=GROQ_TIMEOUT_SECONDS, max_retries=0)
    extra = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        **extra,
    )
    reply = response.choices[0].message.content
    if not reply:
        raise RuntimeError("Groq returned an empty response")
    return reply.strip()
