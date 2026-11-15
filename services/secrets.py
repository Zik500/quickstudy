"""Read API keys from .streamlit/secrets.toml."""

import streamlit as st


def get_secret(name: str):
    """Return a key from .streamlit/secrets.toml, or None if it is missing."""
    try:
        value = st.secrets.get(name)
    except Exception:  # secrets.toml does not exist
        return None
    if not value or str(value).startswith("paste-your"):
        return None  # still the placeholder value
    return value
