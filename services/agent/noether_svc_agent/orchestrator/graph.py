"""LangGraph wiring: router → fan_out → synthesiser → memory_writer → END.

`build_graph` returns a compiled `CompiledGraph`; the caller
`ainvoke({"session_id": ..., "question": ...})`s it. Each node
returns a partial-state dict that LangGraph merges into the running
state, so the order of nodes is the only place that knows the
pipeline shape.

Node functions are intentionally thin — they unpack ChatState, hand
off to a domain object (RouterNode / FanOutNode / etc.), and pack
the result back into the state dict. Domain logic stays unit-testable
without LangGraph in the loop.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from noether_svc_agent.orchestrator.fan_out import FanOutNode
from noether_svc_agent.orchestrator.memory_writer import MemoryWriterNode
from noether_svc_agent.orchestrator.router import RouterNode
from noether_svc_agent.orchestrator.state import ChatState
from noether_svc_agent.orchestrator.synth import SynthesiserNode


def build_graph(
    *,
    router: RouterNode,
    fan_out: FanOutNode,
    synthesiser: SynthesiserNode,
    memory_writer: MemoryWriterNode,
) -> Any:
    """Wire the four nodes into a LangGraph StateGraph and compile.

    Returns the compiled graph; call `await graph.ainvoke({...})` to
    run a turn. The return is `Any` because LangGraph's compiled-
    graph generic type changes between minor versions and pinning it
    here would force a coupled bump on every langgraph upgrade.
    """

    async def router_node(state: ChatState) -> dict[str, Any]:
        names = await router.select_tools(state["question"])
        return {"selected_tools": names}

    async def fan_out_node(state: ChatState) -> dict[str, Any]:
        results = await fan_out.run(state["question"], state["selected_tools"])
        return {"tool_results": results}

    async def synth_node(state: ChatState) -> dict[str, Any]:
        out = await synthesiser.synthesise(
            question=state["question"],
            tool_results=state["tool_results"],
            memories=list(state.get("memories", [])),
        )
        return {
            "answer": out.answer,
            "citations": out.citations,
            "vega_spec": out.vega_spec,
        }

    async def memory_writer_node(state: ChatState) -> dict[str, Any]:
        n = await memory_writer.write_turn(
            session_id=state["session_id"],
            question=state["question"],
            answer=state["answer"],
            tool_results=state["tool_results"],
        )
        return {"facts_written": n}

    g = StateGraph(ChatState)
    g.add_node("router", router_node)
    g.add_node("fan_out", fan_out_node)
    g.add_node("synthesiser", synth_node)
    g.add_node("memory_writer", memory_writer_node)

    g.add_edge(START, "router")
    g.add_edge("router", "fan_out")
    g.add_edge("fan_out", "synthesiser")
    g.add_edge("synthesiser", "memory_writer")
    g.add_edge("memory_writer", END)

    return g.compile()
