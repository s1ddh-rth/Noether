"""SQL tool — read access to `tag_samples` via libs/storage.

Two query modes cover what the chat agent actually needs:

- `latest`: newest sample for one tag. Used by intents like
  "what's FT-101 right now?".
- `range`:  all samples for one tag in a [start, end) window.
  Used by intents like "what was FT-101 doing yesterday at 14:23?".

The wide pivot is intentionally not exposed: forecast / anomaly
intents go through their own tools, which already pull what they
need from `libs/storage` upstream of the agent.

Helper functions are constructor-injected so tests can substitute
fakes without standing up Postgres + Timescale.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Literal

from noether_ingest import TagSample  # type: ignore[import-untyped]
from noether_storage import latest_value, range_query  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from noether_svc_agent.tools.types import ToolResult

LatestFn = Callable[[AsyncEngine, str], Awaitable["TagSample | None"]]
RangeFn = Callable[[AsyncEngine, str, datetime, datetime], Awaitable[list["TagSample"]]]


class SqlToolInput(BaseModel):
    mode: Literal["latest", "range"]
    tag: str = Field(min_length=1)
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def _range_requires_window(self) -> SqlToolInput:
        if self.mode == "range" and (self.start is None or self.end is None):
            raise ValueError("mode='range' requires both `start` and `end`")
        return self


class SqlTool:
    name: str = "sql"
    description: str = (
        "Read recent or historical sensor values from the time-series "
        "store. Use mode='latest' for 'what is X right now', or "
        "mode='range' with start/end ISO-8601 UTC for a window query."
    )

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        latest_fn: LatestFn = latest_value,
        range_fn: RangeFn = range_query,
    ) -> None:
        self._engine = engine
        self._latest_fn = latest_fn
        self._range_fn = range_fn

    async def run(self, input: SqlToolInput) -> ToolResult:
        if input.mode == "latest":
            row = await self._latest_fn(self._engine, input.tag)
            if row is None:
                return ToolResult(
                    summary=f"No samples for {input.tag} in tag_samples.",
                    data={"tag": input.tag, "row": None},
                )
            return ToolResult(
                summary=(
                    f"{input.tag} latest = {row.value:.4f} "
                    f"(quality={row.quality.name}, ts={row.ts.isoformat()})."
                ),
                data={
                    "tag": row.tag,
                    "value": row.value,
                    "quality": row.quality.name,
                    "ts": row.ts.isoformat(),
                },
            )

        # mode='range' — start/end guaranteed non-None by validator.
        assert input.start is not None and input.end is not None
        rows = await self._range_fn(self._engine, input.tag, input.start, input.end)
        values = [r.value for r in rows]
        data: dict[str, Any] = {
            "tag": input.tag,
            "start": input.start.isoformat(),
            "end": input.end.isoformat(),
            "count": len(rows),
            "rows": [
                {"ts": r.ts.isoformat(), "value": r.value, "quality": r.quality.name} for r in rows
            ],
        }
        if values:
            data["min"] = min(values)
            data["max"] = max(values)
            data["mean"] = sum(values) / len(values)
            summary = (
                f"{input.tag} over {input.start.isoformat()}..{input.end.isoformat()}: "
                f"{len(rows)} samples, "
                f"min={data['min']:.4f}, mean={data['mean']:.4f}, max={data['max']:.4f}."
            )
        else:
            summary = (
                f"No samples for {input.tag} between "
                f"{input.start.isoformat()} and {input.end.isoformat()}."
            )

        return ToolResult(summary=summary, data=data)
