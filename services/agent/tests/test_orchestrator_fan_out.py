"""FanOutNode: parallel tool dispatch with input extraction + isolation of failures."""

from __future__ import annotations

import asyncio

import pytest
from noether_svc_agent.orchestrator import FanOutNode, ParamExtractor
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import RagTool, RagToolInput, ToolResult


def _ok_rag_tool(canned: list[ToolResult] | None = None) -> RagTool:
    """RagTool wired to a fake retrieve_fn returning the same canned hits."""

    def fake_retrieve(_q: str, _n: int) -> list[object]:
        return []

    if canned is None:
        return RagTool(retrieve_fn=fake_retrieve)

    # Wrap to return canned ToolResults via tool.run() — easiest hack: subclass.
    class _CannedRag(RagTool):
        async def run(self, _input: RagToolInput) -> ToolResult:  # type: ignore[override]
            return canned[0]

    return _CannedRag(retrieve_fn=fake_retrieve)


@pytest.mark.asyncio
async def test_dispatches_one_tool_with_extracted_input() -> None:
    # Provider serves: param-extraction JSON for rag tool.
    provider = MockProvider(responses=['{"query": "FT-101"}'])
    extractor = ParamExtractor(provider=provider)
    canned = ToolResult(summary="hit", citations=["doc:0"])
    fan = FanOutNode(tools=[_ok_rag_tool([canned])], param_extractor=extractor)

    out = await fan.run("how to calibrate FT-101?", ["rag"])
    assert len(out) == 1
    assert out[0].summary == "hit"
    assert out[0].citations == ["doc:0"]


@pytest.mark.asyncio
async def test_skips_tool_when_input_extraction_fails() -> None:
    provider = MockProvider(responses=["not json"])  # extractor returns None
    extractor = ParamExtractor(provider=provider)
    fan = FanOutNode(tools=[_ok_rag_tool()], param_extractor=extractor)

    out = await fan.run("anything", ["rag"])
    assert out == []


@pytest.mark.asyncio
async def test_unknown_tool_name_skipped_silently() -> None:
    """Defensive — router should already filter, but fan-out doesn't crash on misses."""
    provider = MockProvider(responses=[])
    extractor = ParamExtractor(provider=provider)
    fan = FanOutNode(tools=[_ok_rag_tool()], param_extractor=extractor)

    out = await fan.run("x", ["nonexistent"])
    assert out == []


@pytest.mark.asyncio
async def test_failing_tool_doesnt_poison_siblings() -> None:
    """One tool's exception must not prevent siblings from returning results."""

    class _FlakyTool:
        name = "flaky"
        description = "explodes for testing"
        input_model = RagToolInput

        async def run(self, _input: RagToolInput) -> ToolResult:
            raise RuntimeError("boom")

    canned = ToolResult(summary="rag ok")
    # Two extractions: one for flaky, one for rag. Both return valid JSON.
    provider = MockProvider(responses=['{"query": "x"}', '{"query": "x"}'])
    extractor = ParamExtractor(provider=provider)
    fan = FanOutNode(
        tools=[_FlakyTool(), _ok_rag_tool([canned])],  # type: ignore[list-item]
        param_extractor=extractor,
    )

    out = await fan.run("anything", ["flaky", "rag"])
    # Only rag's result survives — flaky's exception was caught.
    assert len(out) == 1
    assert out[0].summary == "rag ok"


@pytest.mark.asyncio
async def test_runs_tools_concurrently() -> None:
    """asyncio.gather — slow tools should run wall-clock-parallel, not serial."""

    started = 0
    finished_order: list[str] = []

    class _SlowTool:
        def __init__(self, name: str, delay: float) -> None:
            self.name = name
            self.description = "slow"
            self.input_model = RagToolInput
            self._delay = delay

        async def run(self, _input: RagToolInput) -> ToolResult:
            nonlocal started
            started += 1
            await asyncio.sleep(self._delay)
            finished_order.append(self.name)
            return ToolResult(summary=f"{self.name} done")

    provider = MockProvider(
        responses=[
            '{"query": "x"}',  # for "a"
            '{"query": "x"}',  # for "b"
        ]
    )
    extractor = ParamExtractor(provider=provider)
    fan = FanOutNode(
        tools=[_SlowTool("a", 0.10), _SlowTool("b", 0.02)],  # type: ignore[list-item]
        param_extractor=extractor,
    )

    loop = asyncio.get_running_loop()
    t0 = loop.time()
    out = await fan.run("x", ["a", "b"])
    elapsed = loop.time() - t0

    assert {r.summary for r in out} == {"a done", "b done"}
    # If serialised, elapsed >= 0.12 s. Concurrent: max(0.10, 0.02) ≈ 0.10 s + extractor overhead.
    # Param extraction also runs serially per the current FanOutNode impl, so allow some headroom.
    assert elapsed < 0.4, f"fan-out should be concurrent, took {elapsed:.3f}s"
    # b finished before a — proves they ran in parallel.
    assert finished_order == ["b", "a"]
