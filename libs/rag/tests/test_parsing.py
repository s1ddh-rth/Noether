from __future__ import annotations

from pathlib import Path

import pytest
from noether_rag.models import PageText
from noether_rag.parsing import extract_text


def test_extract_text_returns_one_pagetext_per_page(sample_pdf_path: Path) -> None:
    pages = extract_text(sample_pdf_path)
    assert isinstance(pages, list)
    assert all(isinstance(p, PageText) for p in pages)
    assert len(pages) == 2


def test_page_numbers_are_one_indexed_in_order(sample_pdf_path: Path) -> None:
    pages = extract_text(sample_pdf_path)
    assert [p.page_number for p in pages] == [1, 2]


def test_extracted_text_contains_seeded_strings(sample_pdf_path: Path) -> None:
    pages = extract_text(sample_pdf_path)
    page1, page2 = pages
    assert "FT-101" in page1.text
    assert "Steam pressure" in page2.text


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "does-not-exist.pdf")
