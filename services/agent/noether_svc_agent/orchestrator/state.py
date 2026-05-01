"""Shared state passed between orchestrator nodes.

Modeled as a TypedDict so it composes cleanly with LangGraph's
StateGraph (added in a later commit) without any code changes here.
Each node mutates a strict subset of these keys; never mutate
`question`, `session_id`, or `history` after the entry node.
"""

from __future__ import annotations

from typing import Any, TypedDict

from noether_memory import MemoryFact

from noether_svc_agent.providers import Message
from noether_svc_agent.tools.types import ToolResult


class ChatState(TypedDict, total=False):
    # ── Inputs (set by entry node, never mutated) ─────────────────────────
    session_id: str
    question: str
    history: list[Message]
    memories: list[MemoryFact]

    # ── Router output ─────────────────────────────────────────────────────
    selected_tools: list[str]

    # ── Fan-out output ────────────────────────────────────────────────────
    tool_results: list[ToolResult]

    # ── Synthesiser output ────────────────────────────────────────────────
    answer: str
    citations: list[str]
    vega_spec: dict[str, Any] | None

    # ── Memory writer output ──────────────────────────────────────────────
    facts_written: int
