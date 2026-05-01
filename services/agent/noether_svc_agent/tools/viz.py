"""Viz tool — assembles a Vega-Lite line-chart spec from time-series points.

The frontend renders whatever `vega_spec` we hand back, so the tool's
job is purely to emit a valid Vega-Lite v5 line-chart for one or more
named series. No external deps — pure dict construction. Other chart
kinds (scatter, bar, multi-axis) are out of scope at v0.1: Viz v0.1
only needs the line plot to satisfy the M3 demo query (forecast +
recent values overlay).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noether_svc_agent.tools.types import ToolResult


class VizSeriesPoint(BaseModel):
    x: str  # ISO-8601 timestamp; Vega parses it
    y: float


class VizSeries(BaseModel):
    name: str = Field(min_length=1)
    points: list[VizSeriesPoint]


class VizToolInput(BaseModel):
    title: str = Field(min_length=1)
    x_label: str = Field(default="time")
    y_label: str = Field(default="value")
    series: list[VizSeries] = Field(min_length=1)


class VizTool:
    name: str = "viz"
    description: str = (
        "Build a Vega-Lite line chart from one or more named time series. "
        "Use when the user asks for a plot, comparison, or visual overlay."
    )

    async def run(self, input: VizToolInput) -> ToolResult:
        flat_rows = [{"x": p.x, "y": p.y, "series": s.name} for s in input.series for p in s.points]
        spec: dict[str, Any] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": input.title,
            "data": {"values": flat_rows},
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": "x", "type": "temporal", "title": input.x_label},
                "y": {"field": "y", "type": "quantitative", "title": input.y_label},
                "color": {"field": "series", "type": "nominal"},
            },
        }
        return ToolResult(
            summary=f"Built a line chart titled {input.title!r} with "
            f"{len(input.series)} series ({len(flat_rows)} points).",
            data={"point_count": len(flat_rows), "series_count": len(input.series)},
            vega_spec=spec,
        )
