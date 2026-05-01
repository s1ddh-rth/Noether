"""ToolResult shape + AgentTool Protocol conformance."""

from __future__ import annotations

from noether_svc_agent.tools import (
    AgentTool,
    AnomalyTool,
    ForecastTool,
    ToolResult,
    VizTool,
)


def test_tool_result_defaults_match_design_contract() -> None:
    r = ToolResult(summary="ok")
    # Per design.md: data dict|None, citations list, vega_spec dict|None.
    assert r.data is None
    assert r.citations == []
    assert r.vega_spec is None


def test_tool_result_round_trip_through_dict() -> None:
    r = ToolResult(
        summary="found 3 hits",
        data={"hits": 3},
        citations=["doc-a:0", "doc-b:2"],
        vega_spec=None,
    )
    d = r.model_dump()
    assert d["summary"] == "found 3 hits"
    assert d["citations"] == ["doc-a:0", "doc-b:2"]
    # Reconstruct cleanly.
    assert ToolResult.model_validate(d) == r


def test_all_three_tools_satisfy_agent_tool_protocol() -> None:
    """name + description + run — runtime_checkable verifies the shape."""
    viz: AgentTool = VizTool()
    fc: AgentTool = ForecastTool(base_url="http://test", api_key="k")
    an: AgentTool = AnomalyTool(base_url="http://test", api_key="k")
    for t, expected_name in [(viz, "viz"), (fc, "forecast"), (an, "anomaly")]:
        assert isinstance(t, AgentTool)
        assert t.name == expected_name
        assert t.description
