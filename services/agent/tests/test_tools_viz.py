"""VizTool emits a valid Vega-Lite v5 line-chart spec."""

from __future__ import annotations

import pytest
from noether_svc_agent.tools import VizSeries, VizSeriesPoint, VizTool, VizToolInput


@pytest.mark.asyncio
async def test_emits_vega_lite_v5_line_chart() -> None:
    tool = VizTool()
    out = await tool.run(
        VizToolInput(
            title="FT-101 last 5 minutes",
            series=[
                VizSeries(
                    name="actual",
                    points=[
                        VizSeriesPoint(x="2026-04-30T14:23:00Z", y=12.3),
                        VizSeriesPoint(x="2026-04-30T14:24:00Z", y=12.7),
                    ],
                ),
            ],
        )
    )

    assert out.vega_spec is not None
    spec = out.vega_spec
    assert "vega-lite/v5" in spec["$schema"]
    assert spec["title"] == "FT-101 last 5 minutes"
    assert spec["mark"]["type"] == "line"
    assert spec["encoding"]["x"]["type"] == "temporal"
    assert spec["encoding"]["color"]["field"] == "series"
    # The data array got flattened (point, series) tuples.
    assert spec["data"]["values"] == [
        {"x": "2026-04-30T14:23:00Z", "y": 12.3, "series": "actual"},
        {"x": "2026-04-30T14:24:00Z", "y": 12.7, "series": "actual"},
    ]


@pytest.mark.asyncio
async def test_summary_reports_counts() -> None:
    tool = VizTool()
    out = await tool.run(
        VizToolInput(
            title="forecast-vs-actual",
            series=[
                VizSeries(
                    name="forecast", points=[VizSeriesPoint(x="2026-04-30T14:23:00Z", y=12.0)]
                ),
                VizSeries(
                    name="actual",
                    points=[
                        VizSeriesPoint(x="2026-04-30T14:23:00Z", y=11.9),
                        VizSeriesPoint(x="2026-04-30T14:24:00Z", y=12.2),
                    ],
                ),
            ],
        )
    )
    assert out.data == {"point_count": 3, "series_count": 2}
    assert "2 series" in out.summary
    assert "3 points" in out.summary


@pytest.mark.asyncio
async def test_empty_series_list_rejected() -> None:
    """Vega-lite would render nothing — fail validation, not silently produce a blank chart."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VizToolInput(title="t", series=[])
