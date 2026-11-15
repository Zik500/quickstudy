"""Simple checks for PDFs, page ranges and quiz questions."""


def is_empty_pdf(pages: list[str]) -> bool:
    """True if no page has any text (for example a scanned, image-only PDF)."""
    return not "".join(pages).strip()


def looks_scanned(pages: list[str], min_chars_per_page: int) -> bool:
    """True if pages have very little text on average (probably images of pages)."""
    if not pages:
        return False
    return len("".join(pages).strip()) / len(pages) < min_chars_per_page


def is_valid_page_range(first: int, last: int, num_pages: int) -> bool:
    """True if 1 <= first <= last <= num_pages."""
    return 1 <= first <= last <= num_pages


def is_valid_question(question: dict) -> bool:
    """True if a quiz question has exactly 4 DIFFERENT options and its answer is one of them."""
    options = [str(o).strip() for o in question.get("options", [])]
    unique = {o.lower() for o in options}
    return (
        len(options) == 4
        and len(unique) == 4
        and all(options)
        and str(question.get("answer", "")).strip() in options
        and bool(str(question.get("question", "")).strip())
    )
