from __future__ import annotations

from pathlib import Path

import pytest
from noether_rag.parsing import PageImage, extract_page_images
from PIL import Image


def test_returns_one_pageimage_per_page(sample_pdf_path: Path) -> None:
    pages = extract_page_images(sample_pdf_path)
    assert len(pages) == 2
    assert all(isinstance(p, PageImage) for p in pages)


def test_page_numbers_are_one_indexed_in_order(sample_pdf_path: Path) -> None:
    pages = extract_page_images(sample_pdf_path)
    assert [p.page_number for p in pages] == [1, 2]


def test_each_image_has_positive_dimensions(sample_pdf_path: Path) -> None:
    pages = extract_page_images(sample_pdf_path)
    for page in pages:
        assert isinstance(page.image, Image.Image)
        assert page.image.width > 0
        assert page.image.height > 0


def test_dpi_parameter_scales_output(sample_pdf_path: Path) -> None:
    low = extract_page_images(sample_pdf_path, dpi=72)
    high = extract_page_images(sample_pdf_path, dpi=200)
    # Higher DPI must produce larger pixel dimensions.
    assert high[0].image.width > low[0].image.width
    assert high[0].image.height > low[0].image.height


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_page_images(tmp_path / "does-not-exist.pdf")
