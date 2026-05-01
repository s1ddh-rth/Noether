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
    """Anything the orchestrator can dispatch.

    `input_model` is the Pydantic class the orchestrator's parameter
    extractor uses to validate LLM-produced JSON before calling `run`.
    Exposing it on the Protocol lets the fan-out node introspect the
    schema without a per-tool registry — every new tool self-describes.
    """

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def input_model(self) -> type[BaseModel]: ...

    async def run(self, input: BaseModel) -> ToolResult: ...
