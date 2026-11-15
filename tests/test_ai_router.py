"""Tests for the AI router (Groq first, Gemini backup) and Gemini's circuit breaker.
No real API calls: the AI clients are replaced with small fakes."""

import pytest

from actions.schemas import DetailedExplanation
from services import ai_router, gemini_client


def fail(*args, **kwargs):
    raise RuntimeError("Error code: 429 - rate limit")


def test_groq_answers_first(monkeypatch):
    monkeypatch.setattr(ai_router, "groq_chat", lambda *a, **k: "Hello from Groq")
    monkeypatch.setattr(ai_router, "gemini_generate", fail)
    text, label = ai_router.ask_ai([{"role": "user", "content": "Hi"}], max_tokens=100, model="groq-model")
    assert text == "Hello from Groq" and label == "Groq (groq-model)"


def test_gemini_answers_when_groq_fails(monkeypatch):
    monkeypatch.setattr(ai_router, "groq_chat", fail)
    monkeypatch.setattr(ai_router, "gemini_generate", lambda *a, **k: "Hello from Gemini")
    text, label = ai_router.ask_ai([{"role": "user", "content": "Hi"}], max_tokens=100)
    assert text == "Hello from Gemini" and label == ai_router.GEMINI_LABEL


def test_invalid_json_from_groq_goes_to_gemini(monkeypatch):
    monkeypatch.setattr(ai_router, "groq_chat", lambda *a, **k: "Wait... actually the answer is 30%")
    monkeypatch.setattr(ai_router, "gemini_generate",
                        lambda *a, **k: '{"explanation": "12/40 is 30%.", "quote": "ratio = 12/40"}')
    result, label = ai_router.ask_ai_json([{"role": "user", "content": "Explain"}], 100, schema=DetailedExplanation)
    assert result.explanation == "12/40 is 30%." and label == ai_router.GEMINI_LABEL


def test_error_is_raised_when_both_fail(monkeypatch):
    monkeypatch.setattr(ai_router, "groq_chat", fail)
    monkeypatch.setattr(ai_router, "gemini_generate", fail)
    with pytest.raises(RuntimeError):
        ai_router.ask_ai([{"role": "user", "content": "Hi"}], max_tokens=100)


def test_gemini_is_paused_after_503(monkeypatch):
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(1)
            raise RuntimeError("503 UNAVAILABLE: high demand")

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gemini_client, "get_secret", lambda name: "fake-key")
    monkeypatch.setattr(gemini_client, "get_gemini_client", lambda key: FakeClient())
    monkeypatch.setattr(gemini_client.time, "sleep", lambda seconds: None)
    monkeypatch.setitem(gemini_client._breaker, "skip_until", 0.0)

    with pytest.raises(RuntimeError):
        gemini_client.gemini_generate([{"role": "user", "content": "Hi"}], max_tokens=100)
    assert len(calls) == 2  # first try + 1 retry

    # The circuit breaker is open now: Gemini is skipped without calling the API
    with pytest.raises(gemini_client.GeminiUnavailable):
        gemini_client.gemini_generate([{"role": "user", "content": "Hi"}], max_tokens=100)
    assert len(calls) == 2
