"""SynthesiserNode: composes answer + citations + vega_spec deterministically."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from noether_memory import MemoryFact
from noether_svc_agent.orchestrator import SynthesiserNode, SynthesisResult
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import ToolResult


def _result(
    summary: str = "ok",
    *,
    data: dict[str, object] | None = None,
    citations: list[str] | None = None,
    vega_spec: dict[str, object] | None = None,
) -> ToolResult:
    return ToolResult(
        summary=summary,
        data=data,
        citations=citations or [],
        vega_spec=vega_spec,
    )


@pytest.mark.asyncio
async def test_returns_llm_answer_with_aggregated_citations() -> None:
    provider = MockProvider(responses=["FT-101 is at 12.3 [manual-1:0]."])
    synth = SynthesiserNode(provider=provider)

    out = await synth.synthesise(
        question="What is FT-101 right now?",
        tool_results=[
            _result(summary="FT-101=12.3", data={"value": 12.3}),
            _result(summary="rag hit", citations=["manual-1:0"]),
        ],
    )

    assert isinstance(out, SynthesisResult)
    assert out.answer == "FT-101 is at 12.3 [manual-1:0]."
    assert out.citations == ["manual-1:0"]
    assert out.vega_spec is None


@pytest.mark.asyncio
async def test_dedupes_citations_preserving_order() -> None:
    provider = MockProvider(responses=["..."])
    synth = SynthesiserNode(provider=provider)
    out = await synth.synthesise(
        question="x",
        tool_results=[
            _result(citations=["a:0", "b:1"]),
            _result(citations=["b:1", "c:2", "a:0"]),
        ],
    )
    assert out.citations == ["a:0", "b:1", "c:2"]


@pytest.mark.asyncio
async def test_first_non_none_vega_spec_wins() -> None:
    provider = MockProvider(responses=["..."])
    synth = SynthesiserNode(provider=provider)
    spec_a = {"$schema": "v5/a"}
    spec_b = {"$schema": "v5/b"}
    out = await synth.synthesise(
        question="x",
        tool_results=[
            _result(),
            _result(vega_spec=spec_a),
            _result(vega_spec=spec_b),
        ],
    )
    assert out.vega_spec == spec_a


@pytest.mark.asyncio
async def test_empty_tool_results_still_calls_llm() -> None:
    """Synthesiser doesn't short-circuit; the prompt instructs the LLM to admit
    when there's nothing to answer with."""
    provider = MockProvider(responses=["I don't have data to answer that."])
    synth = SynthesiserNode(provider=provider)
    out = await synth.synthesise(question="anything", tool_results=[])
    assert "I don't have data" in out.answer
    assert out.citations == []
    assert out.vega_spec is None


@pytest.mark.asyncio
async def test_prompt_includes_question_and_tool_summaries() -> None:
    """Whatever the LLM does, we must give it the question + tool data."""
    provider = MockProvider(responses=["irrelevant"])
    synth = SynthesiserNode(provider=provider)
    await synth.synthesise(
        question="What is FT-101?",
        tool_results=[_result(summary="FT-101=12.3", data={"value": 12.3})],
    )
    sent_prompt = provider.calls[0].messages[0].content
    assert "What is FT-101?" in sent_prompt
    assert "FT-101=12.3" in sent_prompt
    # Tool data is JSON-serialised in the prompt.
    assert '"value": 12.3' in sent_prompt


@pytest.mark.asyncio
async def test_memories_rendered_into_prompt() -> None:
    provider = MockProvider(responses=["x"])
    synth = SynthesiserNode(provider=provider)
    fact = MemoryFact(
        subject="FT-101",
        predicate="threshold_set",
        object="2.5",
        t_valid=datetime(2026, 4, 30, 14, 23, tzinfo=UTC),
    )
    await synth.synthesise(question="q", tool_results=[], memories=[fact])

    sent = provider.calls[0].messages[0].content
    assert "FT-101 threshold_set 2.5" in sent
    assert "2026-04-30T14:23:00+00:00" in sent


@pytest.mark.asyncio
async def test_oversized_tool_data_truncated_in_prompt_but_not_in_state() -> None:
    """Big tool payloads are truncated for the LLM but the original ToolResult is untouched."""
    provider = MockProvider(responses=["..."])
    synth = SynthesiserNode(provider=provider)

    huge = {"rows": [{"x": i} for i in range(1000)]}
    big_result = _result(summary="big query", data=huge)
    out = await synth.synthesise(question="q", tool_results=[big_result])

    sent_prompt = provider.calls[0].messages[0].content
    # Truncation marker present in the prompt.
    assert "(truncated)" in sent_prompt
    # The result object handed back is whatever the LLM said — but the original
    # tool result wasn't mutated.
    assert big_result.data == huge
    assert out.answer  # non-empty
