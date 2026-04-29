"""PDF parsing via pypdfium2 (Apache-2): text + page-rendered images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from noether_rag.models import PageText


@dataclass(frozen=True, slots=True)
class PageImage:
    """A PDF page rendered as a PIL Image. Use for P&ID-style retrieval."""

    page_number: int
    image: Image.Image


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


def extract_page_images(path: str | Path, dpi: int = 100) -> list[PageImage]:
    """Render each page of `path` as a PIL Image at the given DPI.

    P&IDs delivered as PDFs are typically one diagram per page, so a
    page-render is the natural unit for visual retrieval. pypdfium2's
    `Page.render` takes a `scale` factor where 1.0 = 72 DPI; we convert
    the user-facing DPI to scale here so callers can pass a familiar
    knob.

    Raises:
        FileNotFoundError: if `path` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    scale = dpi / 72.0
    out: list[PageImage] = []
    pdf = pdfium.PdfDocument(str(p))
    try:
        for idx in range(len(pdf)):
            page = pdf[idx]
            try:
                bitmap = page.render(scale=scale)
                try:
                    pil = bitmap.to_pil()
                finally:
                    bitmap.close()
            finally:
                page.close()
            out.append(PageImage(page_number=idx + 1, image=pil))
    finally:
        pdf.close()
    return out
