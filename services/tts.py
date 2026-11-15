"""Text-to-speech with gTTS."""

import io

import gtts
import streamlit as st


@st.cache_data(show_spinner=False)
def text_to_speech(text: str, lang: str) -> bytes:
    """Turn text into MP3 audio in the given language ("en" or "ms")."""
    buffer = io.BytesIO()
    gtts.gTTS(text, lang=lang).write_to_fp(buffer)
    return buffer.getvalue()
