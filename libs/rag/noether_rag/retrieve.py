"""High-level retrieval pipeline: dense + BM25 → RRF → cross-encoder rerank.

Public entrypoint:
    `retrieve(query, *, embedder, qdrant_indexes, bm25_index,
              reranker=None, top_k_fused=20, top_n=5)`

`qdrant_indexes` accepts a list because Phase 2's multimodal path queries
two collections (`noether_mm_bge`, `noether_mm_clip`) and merges them
through the same RRF without any change to this function.
"""

from __future__ import annotations

from noether_rag.embed import Embedder
from noether_rag.fusion import rrf
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.models import RagChunk, RetrievedChunk
from noether_rag.rerank import Reranker

DEFAULT_TOP_K_FUSED = 20
DEFAULT_TOP_N = 5


def retrieve(
    query: str,
    *,
    embedder: Embedder,
    qdrant_indexes: list[QdrantIndex],
    bm25_index: Bm25Index,
    reranker: Reranker | None = None,
    top_k_fused: int = DEFAULT_TOP_K_FUSED,
    top_n: int = DEFAULT_TOP_N,
) -> list[RetrievedChunk]:
    """Run the full hybrid retrieval pipeline for a single query."""
    if not query.strip() or top_n <= 0:
        return []

    query_vec = embedder.encode([query])[0]

    rankings: list[list[str]] = []
    chunks_by_id: dict[str, RagChunk] = {}

    for qi in qdrant_indexes:
        dense_hits = qi.search(query_vec=query_vec, k=top_k_fused)
        rankings.append([chunk.chunk_id for chunk, _ in dense_hits])
        for chunk, _ in dense_hits:
            chunks_by_id.setdefault(chunk.chunk_id, chunk)

    sparse_hits = bm25_index.search(query, k=top_k_fused)
    rankings.append([chunk.chunk_id for chunk, _ in sparse_hits])
    for chunk, _ in sparse_hits:
        chunks_by_id.setdefault(chunk.chunk_id, chunk)

    fused = rrf(rankings)[:top_k_fused]
    fused_chunks = [chunks_by_id[cid] for cid, _ in fused if cid in chunks_by_id]

    if reranker is None:
        # Fall back to RRF score order. Match the API shape by wrapping in
        # RetrievedChunk; cap at top_n.
        return [
            RetrievedChunk(chunk=chunks_by_id[cid], score=score)
            for cid, score in fused[:top_n]
            if cid in chunks_by_id
        ]

    return [
        RetrievedChunk(chunk=chunk, score=score)
        for chunk, score in reranker.rerank(query, fused_chunks, top_n=top_n)
    ]
