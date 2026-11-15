"""Gemini API client: the backup AI for every task, plus vision (reading scanned PDF pages).

Reliability rules:
- 15-second time limit per attempt, and at most 1 retry (after 2 seconds) for 503 / 500 / timeouts.
- Circuit breaker: after a 503, 429 or timeout, Gemini is skipped for 5 minutes,
  so students do not wait for a model that is overloaded.
"""

import time

from google import genai
from google.genai import types
import streamlit as st

from config import GEMINI, GEMINI_COOLDOWN_SECONDS, GEMINI_RETRY_WAITS, GEMINI_TIMEOUT_SECONDS
from services.secrets import get_secret

# Shared by everyone using this app process: when Gemini may be used again
_breaker = {"skip_until": 0.0}


class GeminiUnavailable(RuntimeError):
    """Gemini has no API key, or is skipped for a while by the circuit breaker."""


def gemini_available() -> bool:
    """True if Gemini has a key and is not paused by the circuit breaker."""
    return bool(get_secret("GEMINI_API_KEY")) and time.time() >= _breaker["skip_until"]


def is_temporary_error(e: Exception) -> bool:
    """503 / UNAVAILABLE, 500 / INTERNAL or a timeout: worth one retry."""
    text = f"{type(e).__name__} {e}".lower()
    return any(word in text for word in ["503", "unavailable", "500", "internal", "timeout", "timed out", "deadline"])


def is_overload_error(e: Exception) -> bool:
    """503, 429 / RESOURCE_EXHAUSTED or a timeout: pause Gemini for a while."""
    text = f"{type(e).__name__} {e}".lower()
    return any(word in text for word in ["503", "unavailable", "429", "resource_exhausted", "quota",
                                         "timeout", "timed out", "deadline"])


@st.cache_resource
def get_gemini_client(api_key: str):
    """Create the Gemini client once and reuse it."""
    return genai.Client(api_key=api_key)


def to_gemini_contents(messages: list[dict]):
    """Turn chat messages (role/content) into Gemini's system instruction + contents."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
        for m in messages if m["role"] != "system"
    ]
    return system, contents


def gemini_generate(messages: list[dict], max_tokens: int, json_mode: bool = False, schema=None,
                    images: list[bytes] = None) -> str:
    """Ask Gemini and return the text reply (JSON text if json_mode or schema is set).

    images (PNG bytes) are sent together with the last message (used for scanned PDFs).
    Raises GeminiUnavailable while the circuit breaker is open.
    """
    if not gemini_available():
        raise GeminiUnavailable("Gemini is not available right now")

    system, contents = to_gemini_contents(messages)
    if images:
        image_parts = [types.Part.from_bytes(data=image, mime_type="image/png") for image in images]
        contents[-1].parts = image_parts + contents[-1].parts
    config = types.GenerateContentConfig(
        system_instruction=system or None,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),  # milliseconds
        response_mime_type="application/json" if (json_mode or schema) else None,
        response_schema=schema,
    )

    client = get_gemini_client(get_secret("GEMINI_API_KEY"))
    for attempt in range(len(GEMINI_RETRY_WAITS) + 1):
        try:
            response = client.models.generate_content(model=GEMINI, contents=contents, config=config)
            if not response.text:
                raise RuntimeError("Gemini returned an empty response")
            return response.text
        except Exception as e:
            print(f"[QuickStudy] Gemini attempt {attempt + 1} failed: {e!r}")
            if attempt < len(GEMINI_RETRY_WAITS) and is_temporary_error(e):
                time.sleep(GEMINI_RETRY_WAITS[attempt])
                continue
            if is_overload_error(e):
                _breaker["skip_until"] = time.time() + GEMINI_COOLDOWN_SECONDS
                print(f"[QuickStudy] Gemini paused for {GEMINI_COOLDOWN_SECONDS} seconds")
            raise
