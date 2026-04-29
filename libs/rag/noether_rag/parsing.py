"""PDF text extraction via pypdfium2 (Apache-2)."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from noether_rag.models import PageText


def extract_text(path: str | Path) -> list[PageText]:
    """Return one `PageText` per page of `path`, in document order.

    Page numbers are 1-indexed. Pages that contain no extractable text
    return a `PageText` with `text == ""` so callers can keep alignment
    between page index and chunks.

    Raises:
        FileNotFoundError: if `path` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    pages: list[PageText] = []
    pdf = pdfium.PdfDocument(str(p))
    try:
        for idx in range(len(pdf)):
            page = pdf[idx]
            try:
                tp = page.get_textpage()
                try:
                    text = tp.get_text_bounded()
                finally:
                    tp.close()
            finally:
                page.close()
            pages.append(PageText(page_number=idx + 1, text=text))
    finally:
        pdf.close()
    return pages
