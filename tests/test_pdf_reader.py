"""Tests for utils/pdf_reader.py (rendering pages to images for Gemini Vision)."""

import io

import pypdfium2 as pdfium

from utils.pdf_reader import extract_pdf_pages, render_pages_to_png


def blank_pdf(pages: int) -> bytes:
    """A small PDF with empty pages (like a scanned PDF: no text)."""
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(200, 300)
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


def test_blank_pdf_has_no_text():
    assert extract_pdf_pages(blank_pdf(2)) == ["", ""]


def test_render_only_the_first_pages_as_png():
    images = render_pages_to_png(blank_pdf(3), max_pages=2)
    assert len(images) == 2
    assert all(image.startswith(b"\x89PNG") for image in images)
