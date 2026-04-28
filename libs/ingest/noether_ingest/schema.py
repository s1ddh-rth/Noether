"""Wire schema for plant tag samples.

A `TagSample` is the unit of data on the `plant.tags` topic and the row format
in TimescaleDB. The schema is deliberately minimal — extra metadata belongs in
side-channels (Graphiti, RAG corpus), not on the hot path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Quality(str, Enum):
    GOOD = "good"
    BAD = "bad"
    UNCERTAIN = "uncertain"


class TagSample(BaseModel):
    """One sensor reading at one timestamp."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tag: str = Field(min_length=1, max_length=64)
    value: float
    quality: Quality = Quality.GOOD
    ts: datetime

    @field_validator("ts")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    @field_validator("value")
    @classmethod
    def _reject_nonfinite(cls, v: float) -> float:
        # NaN/Inf can poison downstream models; drop at the boundary.
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("value must be finite")
        return v

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> TagSample:
        return cls.model_validate_json(payload)
