"""Tests for utils/text.py."""

from utils.text import clean_explanation, friendly_error, page_count, slug, strip_markdown, trim_text


def test_clean_explanation_removes_thinking_aloud():
    text = "Wait, correct is 25%. Hmm, let me see. The defect rejection ratio is 12/40 = 30%."
    assert clean_explanation(text) == "The defect rejection ratio is 12/40 = 30%."


def test_clean_explanation_keeps_the_correction_after_actually():
    text = "Wait, is it 25%? Actually, 12/40 = 0.3, so the ratio is 30%."
    assert clean_explanation(text) == "12/40 = 0.3, so the ratio is 30%."


def test_clean_explanation_keeps_at_most_three_sentences():
    assert clean_explanation("One. Two. Three. Four.") == "One. Two. Three."


def test_clean_explanation_keeps_possible_error_message():
    text = "This question may contain an error. The notes say 30%, not 25%."
    assert clean_explanation(text) == text


def test_trim_text_keeps_short_text():
    assert trim_text("hello", 10) == "hello"


def test_trim_text_cuts_long_text():
    assert trim_text("a" * 50, 20) == "a" * 20


def test_strip_markdown_removes_symbols():
    assert strip_markdown("## **Bold** `code` > quote") == " Bold code  quote"


def test_slug_makes_widget_keys():
    assert slug("Audio Tutor") == "audio_tutor"


def test_page_count_singular_and_plural():
    assert page_count({"num_pages": 1}) == "1 page"
    assert page_count({"num_pages": 12}) == "12 pages"


def test_friendly_error_hides_details():
    message = friendly_error(RuntimeError("503 UNAVAILABLE {'error': {'code': 503}}"))
    assert "503" not in message and "{" not in message


def test_friendly_error_rate_limit():
    assert "rate limit" in friendly_error(RuntimeError("Error code: 429"))


def test_friendly_error_keeps_missing_key_message():
    text = "GROQ_API_KEY is missing in .streamlit/secrets.toml"
    assert friendly_error(RuntimeError(text)) == text
