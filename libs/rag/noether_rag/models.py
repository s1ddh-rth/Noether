"""Pydantic models for the RAG pipeline.

`RagChunk.source_type` is left as an open string so Phase 2 can add
multimodal source types (`pid_image`, ...) without a schema rev. The
`SourceType` constants below document the conventional values. Adding a
new value is append-only: define a new constant and document it.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from pydantic import BaseModel, Field

# Stable namespace for chunk point IDs. Do not change — it would invalidate
# every previously-written Qdrant point.
_POINT_NAMESPACE: Final[uuid.UUID] = uuid.UUID("9c2c3d3a-9b3a-4f3a-9c2c-3d3a9b3a4f3a")


class SourceType:
    """Conventional `RagChunk.source_type` values. Append in Phase 2."""

    PDF_TEXT: Final[str] = "pdf_text"
    PID_IMAGE: Final[str] = "pid_image"  # Phase 2 — declared early so the
    # constant is stable and any pre-Phase-2 code referencing it does not
    # need editing when Phase 2 lands.


class PageText(BaseModel):
    """Output of PDF parsing prior to chunking. One per page."""

    page_number: int = Field(ge=1, description="1-indexed page number.")
    text: str


class RagChunk(BaseModel):
    """Atomic unit of retrieval — written to Qdrant + indexed in BM25."""

    doc_id: str = Field(min_length=1)
    chunk_idx: int = Field(ge=0)
    source_type: str = Field(min_length=1)
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """Human-readable id: `{doc_id}:{chunk_idx}`. Stable across reruns."""
        return f"{self.doc_id}:{self.chunk_idx}"

    @property
    def point_uuid(self) -> str:
        """Qdrant point ID — UUIDv5 over `(doc_id, chunk_idx)`.

        Re-ingesting the same chunk (same doc_id + chunk_idx) with edited
        text resolves to the same point UUID, so Qdrant overwrites in place
        and we get idempotency for free.
        """
        return str(uuid.uuid5(_POINT_NAMESPACE, self.chunk_id))


class RetrievedChunk(BaseModel):
    """A chunk returned from the retrieval pipeline, with its final score."""

    chunk: RagChunk
    score: float
