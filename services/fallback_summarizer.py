"""Offline fallback summary with sumy TextRank (no API key needed)."""

import nltk
import streamlit as st
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer

from config import FALLBACK_SENTENCES


@st.cache_resource
def ensure_nltk_data():
    """sumy needs NLTK's 'punkt' tokenizer data; download it once if missing."""
    for name in ["punkt", "punkt_tab"]:
        try:
            nltk.data.find(f"tokenizers/{name}")
        except LookupError:
            nltk.download(name, quiet=True)


def notes_with_sumy(text: str) -> str:
    """Offline fallback: pick the most important sentences with TextRank."""
    ensure_nltk_data()
    clean_text = " ".join(text.split())  # PDFs often break lines mid-sentence
    parser = PlaintextParser.from_string(clean_text, Tokenizer("english"))
    sentences = TextRankSummarizer()(parser.document, FALLBACK_SENTENCES)
    return "### Key Sentences\n" + "\n".join(f"- {s}" for s in sentences)
