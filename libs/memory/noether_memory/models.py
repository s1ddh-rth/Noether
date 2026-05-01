"""Typed memory primitives shared across stores."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class MemoryFact(BaseModel):
    """A single subject-predicate-object fact bound to a valid-time.

    `t_valid` is the time the fact became true (e.g. an operator
    threshold tweak applied at 14:23). Defaults to "now (UTC)" so
    callers extracting facts from a chat turn don't have to compute it.
    """

    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    t_valid: datetime = Field(default_factory=lambda: datetime.now(UTC))
