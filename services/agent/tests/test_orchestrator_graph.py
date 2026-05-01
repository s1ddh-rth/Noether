"""End-to-end LangGraph wiring: question → answer with mocks throughout."""

from __future__ import annotations

import pytest
from noether_memory import InMemoryStore
from noether_svc_agent.orchestrator import (
    FanOutNode,
    MemoryWriterNode,
    ParamExtractor,
    RouterNode,
    SynthesiserNode,
    build_graph,
)
from noether_svc_agent.providers import MockProvider
from noether_svc_agent.tools import RagTool, RagToolInput, ToolResult


def _stub_rag_tool(*, summary: str, citations: list[str]) -> RagTool:
    canned = ToolResult(summary=summary, citations=citations)

    class _Stub(RagTool):
        async def run(self, _input: RagToolInput) -> ToolResult:  # type: ignore[override]
            return canned

    return _Stub(retrieve_fn=lambda q, n: [])


@pytest.mark.asyncio
async def test_full_pipeline_demo_query() -> None:
    """The M3 demo question shape: route → fan-out → synth → memory write.

    Provider response sequence drives the whole pipeline:
      1) router       → '{"tools": ["rag"]}'
      2) param        → '{"query": "calibration drift FT-101"}'
      3) synthesiser  → "FT-101 alert was a calibration drift [doc-1:0]."
      4) memory writer→ '[{"subject":"alert","predicate":"root_cause","object":"calibration_drift"}]'
    """
    provider = MockProvider(
        responses=[
            '{"tools": ["rag"]}',
            '{"query": "calibration drift FT-101"}',
            "FT-101 alert was a calibration drift [doc-1:0].",
            '[{"subject": "alert", "predicate": "root_cause", "object": "calibration_drift"}]',
        ],
    )
    rag = _stub_rag_tool(summary="calibration drift section", citations=["doc-1:0"])

    router = RouterNode(provider=provider, tools=[rag])  # type: ignore[list-item]
    fan_out = FanOutNode(tools=[rag], param_extractor=ParamExtractor(provider=provider))  # type: ignore[list-item]
    synth = SynthesiserNode(provider=provider)
    store = InMemoryStore()
    memw = MemoryWriterNode(provider=provider, store=store)

    graph = build_graph(
        router=router,
        fan_out=fan_out,
        synthesiser=synth,
        memory_writer=memw,
    )

    final = await graph.ainvoke(
        {
            "session_id": "sess-1",
            "question": "Why did the FT-101 alert fire yesterday at 14:23?",
        }
    )

    # Router selected rag.
    assert final["selected_tools"] == ["rag"]
    # Fan-out produced one tool result with the canned content.
    assert len(final["tool_results"]) == 1
    # Synthesiser composed the answer + citations from the tool result.
    assert "calibration drift" in final["answer"]
    assert "doc-1:0" in final["answer"]
    assert final["citations"] == ["doc-1:0"]
    assert final["vega_spec"] is None
    # Memory writer persisted one fact.
    assert final["facts_written"] == 1
    # And it actually landed in the store.
    persisted = await store.retrieve("sess-1", query="alert", k=10)
    assert len(persisted) == 1
    assert persisted[0].predicate == "root_cause"
    assert persisted[0].object == "calibration_drift"


@pytest.mark.asyncio
async def test_pipeline_with_no_tools_selected_still_produces_answer() -> None:
    """If router falls back / picks nothing, synthesiser still runs."""
    # Router emits empty tools — synthesiser should answer "I don't have data".
    provider = MockProvider(
        responses=[
            '{"tools": []}',  # router picks nothing
            "I don't have enough data to answer that.",  # synth
            "[]",  # memory writer extracts nothing
        ]
    )
    router = RouterNode(provider=provider, tools=[])
    fan_out = FanOutNode(tools=[], param_extractor=ParamExtractor(provider=provider))
    synth = SynthesiserNode(provider=provider)
    memw = MemoryWriterNode(provider=provider, store=InMemoryStore())

    graph = build_graph(router=router, fan_out=fan_out, synthesiser=synth, memory_writer=memw)
    final = await graph.ainvoke({"session_id": "s", "question": "obscure"})

    assert final["selected_tools"] == []
    assert final["tool_results"] == []
    assert "don't have enough data" in final["answer"]
    assert final["citations"] == []
    assert final["facts_written"] == 0
