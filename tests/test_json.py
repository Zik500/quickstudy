"""Tests for parse_json in utils/text.py (reading JSON replies from the AI)."""

import pytest

from utils.text import parse_json


def test_parse_simple_object():
    assert parse_json('{"answer": "Yes", "sources": []}') == {"answer": "Yes", "sources": []}


def test_parse_allows_line_breaks_inside_strings():
    data = parse_json('{"answer": "Line 1\nLine 2"}')
    assert data["answer"] == "Line 1\nLine 2"


def test_parse_rejects_a_list():
    with pytest.raises(ValueError):
        parse_json("[1, 2, 3]")


def test_parse_rejects_text_that_is_not_json():
    with pytest.raises(ValueError):
        parse_json("Sorry, I cannot help with that.")
