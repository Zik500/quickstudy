"""Tests for utils/validators.py."""

from utils.validators import is_empty_pdf, is_valid_page_range, is_valid_question, looks_scanned


def make_question(options, answer):
    return {"question": "What is 12/40 as a percentage?", "options": options, "answer": answer}


def test_empty_pdf_detected():
    assert is_empty_pdf(["", "   ", "\n"])


def test_pdf_with_text_is_not_empty():
    assert not is_empty_pdf(["", "Chapter 1"])


def test_scanned_pdf_has_little_text_per_page():
    assert looks_scanned(["", "Page 2", ""], min_chars_per_page=200)
    assert not looks_scanned(["x" * 500, "y" * 300], min_chars_per_page=200)


def test_valid_page_ranges():
    assert is_valid_page_range(1, 1, 1)
    assert is_valid_page_range(2, 5, 10)


def test_invalid_page_ranges():
    assert not is_valid_page_range(0, 3, 10)   # pages start at 1
    assert not is_valid_page_range(5, 2, 10)   # first after last
    assert not is_valid_page_range(1, 11, 10)  # past the end


def test_valid_question():
    assert is_valid_question(make_question(["25%", "30%", "35%", "40%"], "30%"))


def test_question_needs_four_options():
    assert not is_valid_question(make_question(["25%", "30%", "35%"], "30%"))


def test_question_options_must_be_different():
    assert not is_valid_question(make_question(["30%", "30%", "35%", "40%"], "30%"))
    assert not is_valid_question(make_question(["Fault", "fault", "Bug", "Error"], "Bug"))  # case-insensitive


def test_answer_must_be_one_of_the_options():
    assert not is_valid_question(make_question(["25%", "35%", "40%", "45%"], "30%"))
