"""RAG tool — `libs/rag.retrieve` wrapped behind the AgentTool contract.

`retrieve()` is synchronous (sentence-transformers + Qdrant client are
blocking) so the tool offloads to a thread. The orchestrator stays
fully async; the heavy work runs on the asyncio threadpool.

Two flavours: text (`RagTool`) and multimodal (`MultimodalRagTool`).
They share all behaviour — only `name`, `description`, and the bound
retrieve_fn differ. The split exists so the router can dispatch the
two intents distinctly per the design.

The retrieve callable is constructor-injected. In production the
factory binds it to a real `embedder + qdrant_indexes + bm25_index +
reranker` quartet; tests pass a synchronous fake that returns canned
`RetrievedChunk`s, side-stepping Qdrant + BGE entirely.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from noether_rag import RetrievedChunk  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from noether_svc_agent.tools.types import ToolResult

RetrieveFn = Callable[[str, int], list["RetrievedChunk"]]


class RagToolInput(BaseModel):
    query: str = Field(min_length=1)
    top_n: int = Field(default=5, ge=1, le=50)


class _RagToolBase:
    name: str = "rag"
    description: str = (
        "Search technical documentation (PDFs, manuals) for context "
        "relevant to the user's question. Returns short excerpts with "
        "doc_id:chunk_idx citations."
    )

    def __init__(self, retrieve_fn: RetrieveFn) -> None:
        self._retrieve_fn = retrieve_fn

    async def run(self, input: RagToolInput) -> ToolResult:
        hits = await asyncio.to_thread(self._retrieve_fn, input.query, input.top_n)
        if not hits:
            return ToolResult(
                summary=f"No documentation hits for {input.query!r}.",
                data={"hits": []},
                citations=[],
            )

        citations = [h.chunk.chunk_id for h in hits]
        # Bound the summary preview length per chunk so the synthesiser
        # doesn't have to deal with a wall of text — full text is in `data`.
        previews = [
            f"[{h.chunk.chunk_id}] {h.chunk.text[:160].strip()}{'...' if len(h.chunk.text) > 160 else ''}"
            for h in hits
        ]
        summary = "\n".join(previews)
        return ToolResult(
            summary=summary,
            data={
                "hits": [
                    {
                        "chunk_id": h.chunk.chunk_id,
                        "doc_id": h.chunk.doc_id,
                        "chunk_idx": h.chunk.chunk_idx,
                        "source_type": h.chunk.source_type,
                        "text": h.chunk.text,
                        "score": h.score,
                    }
                    for h in hits
                ],
            },
            citations=citations,
        )


class RagTool(_RagToolBase):
    """Text RAG over the BGE/BM25 hybrid indexes."""


class MultimodalRagTool(_RagToolBase):
    """P&ID retrieval over the OpenCLIP multimodal index.

    Same shape as `RagTool` — only the bound retrieve_fn differs (it
    queries the multimodal Qdrant collection and filters on
    `source_type='pid_image'`). Kept as a distinct class so the router
    can pick it explicitly when the user asks about a P&ID, instrument
    diagram, or piping layout.
    """

    name: str = "multimodal_rag"
    description: str = (
        "Search piping & instrumentation diagrams (P&IDs) for "
        "instruments, valves, lines, or layouts. Use when the user "
        "mentions a tag with a position on a diagram (FT-101, V-203, "
        "loop sheets) or asks about equipment topology."
    )
