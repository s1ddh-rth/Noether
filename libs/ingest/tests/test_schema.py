from datetime import UTC, datetime

import pytest
from noether_ingest import Quality, TagSample
from pydantic import ValidationError


def test_happy_path_round_trip() -> None:
    sample = TagSample(
        tag="XMEAS_1",
        value=42.5,
        ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    payload = sample.to_kafka_payload()
    restored = TagSample.from_kafka_payload(payload)
    assert restored == sample
    assert restored.quality is Quality.GOOD


def test_naive_timestamp_coerced_to_utc() -> None:
    sample = TagSample(tag="XMEAS_1", value=1.0, ts=datetime(2026, 1, 1, 12, 0))
    assert sample.ts.tzinfo == UTC


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_value_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        TagSample(tag="XMEAS_1", value=bad, ts=datetime.now(tz=UTC))


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        TagSample.model_validate(
            {
                "tag": "XMEAS_1",
                "value": 1.0,
                "ts": "2026-01-01T00:00:00Z",
                "rogue_extra": True,
            }
        )
