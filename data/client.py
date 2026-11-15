"""Create the Supabase client from st.secrets (SUPABASE_URL and SUPABASE_KEY)."""

import streamlit as st
from supabase import create_client


@st.cache_resource
def _connect(url: str, key: str):
    """Create the client once and reuse it."""
    return create_client(url, key)


def get_client():
    """The Supabase client, or None if Supabase is not configured in .streamlit/secrets.toml."""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:  # secrets.toml does not exist
        return None
    if not url or not key or str(url).startswith("paste-your") or str(key).startswith("paste-your"):
        return None
    try:
        return _connect(url, key)
    except Exception as e:
        print(f"[QuickStudy] could not connect to Supabase: {e!r}")
        return None


def db():
    """The Supabase client for repository functions. Raises if Supabase is not available."""
    client = get_client()
    if client is None:
        raise RuntimeError("Supabase is not configured")
    return client
