"""Synthesiser node — composes the final answer from tool results.

Takes the question, the tool results from the fan-out node, and any
retrieved memories. Calls the LLM once to produce the natural-language
answer. The non-LLM bits (citation aggregation, vega_spec selection)
are deterministic and happen here, not via the LLM, so they're
test-pinnable without any model in the loop.
"""

from __future__ import annotations

import json
from typing import Any

from noether_memory import MemoryFact
from pydantic import BaseModel

from noether_svc_agent.prompts import load_prompt
from noether_svc_agent.providers import Message, Provider
from noether_svc_agent.tools.types import ToolResult

# Cap how much of each tool result body we put in the prompt — local
# LLMs choke on context windows past ~8k tokens. Full data still lives
# in `state["tool_results"]` for downstream consumers.
PROMPT_TOOL_RESULT_CHAR_CAP = 1500


class SynthesisResult(BaseModel):
    """The slice of ChatState the synthesiser produces."""

    answer: str
    citations: list[str]
    vega_spec: dict[str, Any] | None


class SynthesiserNode:
    def __init__(self, provider: Provider) -> None:
        self._provider = provider
        self._prompt_template = load_prompt("synthesiser")

    async def synthesise(
        self,
        question: str,
        tool_results: list[ToolResult],
        memories: list[MemoryFact] | None = None,
    ) -> SynthesisResult:
        memories = memories or []

        # Aggregate citations preserving order, deduplicated.
        citations: list[str] = []
        seen: set[str] = set()
        for r in tool_results:
            for c in r.citations:
                if c not in seen:
                    citations.append(c)
                    seen.add(c)

        # First non-None vega_spec wins — design.md Viz is "?" (optional, one).
        vega_spec = next((r.vega_spec for r in tool_results if r.vega_spec is not None), None)

        prompt = self._prompt_template.format(
            question=question,
            tool_results=self._format_tool_results(tool_results),
            memories=self._format_memories(memories),
        )

        response = await self._provider.chat([Message(role="user", content=prompt)])
        return SynthesisResult(
            answer=response.content.strip(),
            citations=citations,
            vega_spec=vega_spec,
        )

    def _format_tool_results(self, results: list[ToolResult]) -> str:
        if not results:
            return "(none)"
        rendered: list[str] = []
        for r in results:
            payload: dict[str, Any] = {"summary": r.summary}
            if r.data is not None:
                payload["data"] = r.data
            if r.citations:
                payload["citations"] = r.citations
            text = json.dumps(payload, default=str)
            if len(text) > PROMPT_TOOL_RESULT_CHAR_CAP:
                text = text[:PROMPT_TOOL_RESULT_CHAR_CAP] + "...(truncated)"
            rendered.append(text)
        return "\n\n".join(rendered)

    def _format_memories(self, memories: list[MemoryFact]) -> str:
        if not memories:
            return "(none)"
        return "\n".join(
            f"- ({m.subject} {m.predicate} {m.object}) at {m.t_valid.isoformat()}" for m in memories
        )
