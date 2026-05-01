"""SqlTool: latest + range modes; helper-fn injection avoids needing Postgres."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from noether_ingest import Quality, TagSample
from noether_svc_agent.tools import SqlTool, SqlToolInput
from sqlalchemy.ext.asyncio import AsyncEngine


def _sample(value: float, *, ts: datetime, tag: str = "FT-101") -> TagSample:
    return TagSample(tag=tag, value=value, quality=Quality.GOOD, ts=ts)


# A sentinel object for the engine arg — the injected fns ignore it,
# but we need *something* of a recognizable type for SqlTool to accept.
class _FakeEngine:
    pass


_FAKE_ENGINE: AsyncEngine = _FakeEngine()  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_latest_returns_value_with_quality_and_ts() -> None:
    ts = datetime(2026, 4, 30, 14, 23, tzinfo=UTC)

    async def fake_latest(_engine: AsyncEngine, tag: str) -> TagSample | None:
        assert tag == "FT-101"
        return _sample(12.345, ts=ts)

    async def fake_range(*_args: object, **_kwargs: object) -> list[TagSample]:
        raise AssertionError("range_fn should not be called for mode='latest'")

    tool = SqlTool(_FAKE_ENGINE, latest_fn=fake_latest, range_fn=fake_range)
    out = await tool.run(SqlToolInput(mode="latest", tag="FT-101"))

    assert "12.3450" in out.summary
    assert "GOOD" in out.summary
    assert out.data is not None
    assert out.data["value"] == 12.345
    assert out.data["quality"] == "GOOD"


@pytest.mark.asyncio
async def test_latest_no_rows() -> None:
    async def fake_latest(_e: AsyncEngine, _t: str) -> TagSample | None:
        return None

    async def fake_range(*_a: object, **_k: object) -> list[TagSample]:
        return []

    tool = SqlTool(_FAKE_ENGINE, latest_fn=fake_latest, range_fn=fake_range)
    out = await tool.run(SqlToolInput(mode="latest", tag="missing"))
    assert "No samples" in out.summary
    assert out.data is not None
    assert out.data["row"] is None


@pytest.mark.asyncio
async def test_range_summarises_min_mean_max() -> None:
    start = datetime(2026, 4, 30, 14, 0, tzinfo=UTC)
    end = start + timedelta(minutes=5)

    async def fake_latest(*_a: object, **_k: object) -> TagSample | None:
        raise AssertionError("latest_fn not used for mode='range'")

    async def fake_range(
        _e: AsyncEngine,
        tag: str,
        s: datetime,
        e: datetime,
    ) -> list[TagSample]:
        assert tag == "FT-101"
        assert s == start and e == end
        return [_sample(v, ts=start + timedelta(minutes=i)) for i, v in enumerate([1.0, 2.0, 3.0])]

    tool = SqlTool(_FAKE_ENGINE, latest_fn=fake_latest, range_fn=fake_range)
    out = await tool.run(SqlToolInput(mode="range", tag="FT-101", start=start, end=end))

    assert "3 samples" in out.summary
    assert "min=1.0000" in out.summary
    assert "mean=2.0000" in out.summary
    assert "max=3.0000" in out.summary
    assert out.data is not None
    assert out.data["count"] == 3
    assert len(out.data["rows"]) == 3


@pytest.mark.asyncio
async def test_range_empty_window() -> None:
    start = datetime(2026, 4, 30, 14, 0, tzinfo=UTC)
    end = start + timedelta(minutes=5)

    async def fake_range(*_a: object, **_k: object) -> list[TagSample]:
        return []

    tool = SqlTool(_FAKE_ENGINE, latest_fn=lambda *a: None, range_fn=fake_range)  # type: ignore[arg-type]
    out = await tool.run(SqlToolInput(mode="range", tag="FT-101", start=start, end=end))
    assert "No samples" in out.summary
    assert out.data is not None
    assert out.data["count"] == 0
    assert "min" not in out.data


def test_range_mode_requires_start_and_end() -> None:
    """Missing window on range mode is a validation error, not a runtime hang."""
    from pydantic import ValidationError

    start = datetime(2026, 4, 30, 14, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match=r"start.*end"):
        SqlToolInput(mode="range", tag="FT-101", start=start)
    with pytest.raises(ValidationError, match=r"start.*end"):
        SqlToolInput(mode="range", tag="FT-101", end=start)
