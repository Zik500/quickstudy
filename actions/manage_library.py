"""Action: add a PDF to the notes library, or remove one."""

import hashlib

import streamlit as st

from actions.generate_outline import make_outline
from actions.schemas import PageTexts
from actions.sync_data import delete_file, save_file
from config import MIN_CHARS_PER_PAGE, VISION_MAX_PAGES
from services.gemini_client import gemini_generate
from state import log_activity
from utils.pdf_reader import extract_pdf_pages, render_pages_to_png
from utils.text import parse_json
from utils.validators import is_empty_pdf, looks_scanned


def read_with_vision(pdf_bytes: bytes) -> list[str]:
    """Read a scanned PDF with Gemini Vision: the first pages are sent as images.
    Returns the text of each page that was read."""
    images = render_pages_to_png(pdf_bytes, VISION_MAX_PAGES)
    messages = [
        {"role": "system", "content": "You read scanned lecture notes. Copy the text of each page exactly, "
                                      "in reading order. Do not summarise or add anything."},
        {"role": "user", "content": f"Extract the text of these {len(images)} pages. "
                                    'Reply with JSON: {"pages": ["text of page 1", "text of page 2", ...]}'},
    ]
    raw = gemini_generate(messages, max_tokens=8000, schema=PageTexts, images=images)
    return [str(page).strip() for page in PageTexts.model_validate(parse_json(raw)).pages]


def add_to_library(uploaded_file) -> bool:
    """Add a PDF to the library (no duplicates) and select it. Returns True if it has text."""
    pdf_bytes = uploaded_file.getvalue()
    pdf_hash = hashlib.md5(pdf_bytes).hexdigest()
    library = st.session_state.library

    # Same file uploaded again? Then just select it (no duplicate)
    file_id = next((name for name, info in library.items() if info["hash"] == pdf_hash), None)
    if file_id is None:
        # A different file with the same name gets " (2)", " (3)", ...
        file_id = uploaded_file.name
        number = 2
        while file_id in library:
            base, dot, ext = uploaded_file.name.rpartition(".")
            file_id = f"{base} ({number}).{ext}" if dot else f"{uploaded_file.name} ({number})"
            number += 1
        try:
            pages = extract_pdf_pages(pdf_bytes)
        except Exception:
            st.session_state.upload_error = f"Could not read {uploaded_file.name}. Please try another file."
            return False

        # Very little text = probably a scanned PDF: let Gemini Vision read the first pages
        text_source = "pypdf"
        if looks_scanned(pages, MIN_CHARS_PER_PAGE):
            try:
                vision_pages = read_with_vision(pdf_bytes)
                if "".join(vision_pages).strip():
                    pages = vision_pages + pages[len(vision_pages):]
                    text_source = "Gemini Vision"
            except Exception as e:
                print(f"[QuickStudy] Gemini Vision could not read {uploaded_file.name}: {e!r}")

        if is_empty_pdf(pages):
            st.session_state.upload_error = (
                f"No text could be extracted from {uploaded_file.name}. "
                "It may be a scanned image, and Gemini Vision could not read it right now. "
                "Try again later or use a text-based PDF."
            )
            return False
        library[file_id] = {
            "name": file_id,
            "hash": pdf_hash,
            "pages": pages,
            "text": "\n".join(pages),
            "num_pages": len(pages),
            "outline": None,            # list of {"title", "description"}, made once by the AI
            "text_source": text_source,  # "pypdf" or "Gemini Vision"
        }
        st.session_state[f"pages_{file_id}"] = (1, len(pages))  # default page range: all pages
        make_outline(file_id)
        save_file(file_id)  # Supabase (skipped in offline mode)
        log_activity("upload", "", file_id)

    # Select the new file everywhere
    st.session_state.upload_error = ""
    st.session_state.current_file = file_id
    for key in ["chat_files", "quiz_files"]:
        selected = st.session_state.get(key, [])
        if file_id not in selected:
            st.session_state[key] = selected + [file_id]
    return True


def remove_from_library(file_id: str):
    """Remove a PDF and everything cached for it (used as a button callback)."""
    info = st.session_state.library.pop(file_id, None)
    if info:
        delete_file(info)  # Supabase (its notes are deleted too)
    notes_cache, tutor_cache = st.session_state.notes_cache, st.session_state.tutor_cache
    for key in [k for k in notes_cache if k.startswith(f"{file_id}|")]:
        del notes_cache[key]
    for key in [k for k in tutor_cache if k.startswith(f"notes_{file_id}_")]:
        del tutor_cache[key]
    for key in ["chat_files", "quiz_files"]:
        st.session_state[key] = [f for f in st.session_state.get(key, []) if f != file_id]
    if st.session_state.get("current_file") == file_id:
        st.session_state.current_file = next(reversed(st.session_state.library), None)
    st.session_state.pop(f"pages_{file_id}", None)
