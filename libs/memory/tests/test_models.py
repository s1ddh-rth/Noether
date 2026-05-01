"""MemoryFact validation and defaults."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from noether_memory import MemoryFact
from pydantic import ValidationError


def test_t_valid_defaults_to_utc_now() -> None:
    before = datetime.now(UTC)
    fact = MemoryFact(subject="FT-101", predicate="threshold", object="2.5")
    after = datetime.now(UTC)
    assert before <= fact.t_valid <= after
    assert fact.t_valid.tzinfo is not None


def test_explicit_t_valid_is_preserved() -> None:
    ts = datetime(2026, 4, 30, 14, 23, tzinfo=UTC)
    fact = MemoryFact(subject="FT-101", predicate="anomaly_fired", object="14:23", t_valid=ts)
    assert fact.t_valid == ts


def test_empty_strings_rejected() -> None:
    with pytest.raises(ValidationError):
        MemoryFact(subject="", predicate="p", object="o")
    with pytest.raises(ValidationError):
        MemoryFact(subject="s", predicate="", object="o")
    with pytest.raises(ValidationError):
        MemoryFact(subject="s", predicate="p", object="")
