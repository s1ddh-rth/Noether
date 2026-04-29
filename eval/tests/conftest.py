"""Re-export of the libs/rag sample-PDF fixture for eval tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from noether_rag.tests_helpers import sample_pdf_bytes


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Iterator[Path]:
    p = tmp_path / "sample.pdf"
    p.write_bytes(sample_pdf_bytes())
    yield p
