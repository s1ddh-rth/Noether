"""LangGraph-style orchestration for the chat service.

Each node is a plain `async def` taking and returning a `ChatState` dict.
The full StateGraph that chains them lands in a follow-up commit; for
now each node is unit-testable in isolation against a `MockProvider`.

Pipeline (per design.md):

    router → fan-out (parallel tools) → synthesiser → memory writer
"""

from noether_svc_agent.orchestrator.memory_writer import MemoryWriterNode
from noether_svc_agent.orchestrator.router import RouterNode
from noether_svc_agent.orchestrator.state import ChatState
from noether_svc_agent.orchestrator.synth import SynthesiserNode, SynthesisResult

__all__ = [
    "ChatState",
    "MemoryWriterNode",
    "RouterNode",
    "SynthesisResult",
    "SynthesiserNode",
]
