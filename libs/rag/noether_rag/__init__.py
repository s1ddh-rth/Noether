"""Hybrid retrieval over technical PDFs.

Public API (Phase 1 — text-only):
    RagChunk           — payload model carried through ingest -> retrieve
    RetrievedChunk     — RagChunk + score
    PageText           — output of PDF parsing prior to chunking
    SourceType         — string constants for `RagChunk.source_type`
    chunk_text         — recursive character chunker
    extract_text       — PDF -> list[PageText] via pypdfium2
    Embedder           — Protocol; implemented by BgeTextEmbedder
    BgeTextEmbedder    — BAAI/bge-base-en-v1.5
    Reranker           — Protocol; implemented by BgeReranker
    BgeReranker        — BAAI/bge-reranker-base
    QdrantIndex        — collection bootstrap, upsert, search
    Bm25Index          — sparse retrieval + pickled persistence
    rrf                — reciprocal rank fusion (k=60)
    retrieve           — hybrid pipeline: dense + BM25 -> RRF -> rerank

Phase 2 will add multimodal embedders (BGE-M3, OpenCLIP) behind the same
`Embedder` protocol and reuse `rrf` / `QdrantIndex` unchanged.
"""

from noether_rag.chunker import chunk_text
from noether_rag.embed import BgeTextEmbedder, Embedder
from noether_rag.fusion import rrf
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.models import PageText, RagChunk, RetrievedChunk, SourceType
from noether_rag.parsing import extract_text
from noether_rag.rerank import BgeReranker, Reranker
from noether_rag.retrieve import retrieve

__all__ = [
    "BgeReranker",
    "BgeTextEmbedder",
    "Bm25Index",
    "Embedder",
    "PageText",
    "QdrantIndex",
    "RagChunk",
    "Reranker",
    "RetrievedChunk",
    "SourceType",
    "chunk_text",
    "extract_text",
    "retrieve",
    "rrf",
]
