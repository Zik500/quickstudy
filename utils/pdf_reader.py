"""Read text from PDF files, and turn pages into images (for scanned PDFs)."""

import io

from pypdf import PdfReader
import pypdfium2 as pdfium


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """Read the text of every page. Scanned (image-only) pages give ""."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def render_pages_to_png(pdf_bytes: bytes, max_pages: int, scale: float = 1.5) -> list[bytes]:
    """Render the first max_pages pages as PNG images (for Gemini Vision)."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    images = []
    try:
        for index in range(min(len(pdf), max_pages)):
            image = pdf[index].render(scale=scale).to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            images.append(buffer.getvalue())
    finally:
        pdf.close()
    return images
