"""Tool contract: `ToolResult` + `AgentTool` Protocol.

`ToolResult` is what every sub-agent returns to the synthesiser. The
synthesiser must:

- treat `summary` as a one-paragraph natural-language description it
  can interpolate into the final answer;
- include any items in `citations` (typically `doc_id:chunk_idx` from
  RAG hits) verbatim in the response;
- pass `vega_spec` straight through to the frontend if non-None.

`data` is the structured payload (rows, scores, intervals) that the
synthesiser may inspect when composing the answer.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    summary: str
    data: dict[str, Any] | None = None
    citations: list[str] = Field(default_factory=list)
    vega_spec: dict[str, Any] | None = None


@runtime_checkable
class AgentTool(Protocol):
    """Anything the orchestrator can dispatch."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def run(self, input: BaseModel) -> ToolResult: ...
