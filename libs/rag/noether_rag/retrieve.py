"""High-level retrieval pipeline: dense + BM25 → RRF → cross-encoder rerank.

Public entrypoint:
    `retrieve(query, *, embedder, qdrant_indexes, bm25_index,
              reranker=None, top_k_fused=20, top_n=5)`

`qdrant_indexes` accepts a list of either bare `QdrantIndex` (encoded with
the top-level `embedder`) or `(QdrantIndex, Embedder)` tuples — Phase 2's
multimodal path uses the tuple form so the OpenCLIP image collection is
queried with the OpenCLIP text encoder, while the BGE text collection is
queried with `BgeTextEmbedder`. Both rankings still merge through RRF
unchanged.
"""

from __future__ import annotations

from noether_rag.embed import Embedder
from noether_rag.fusion import rrf
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.models import RagChunk, RetrievedChunk
from noether_rag.rerank import Reranker

DEFAULT_TOP_K_FUSED = 20
DEFAULT_TOP_N = 5

QdrantIndexSpec = QdrantIndex | tuple[QdrantIndex, Embedder]


def retrieve(
    query: str,
    *,
    embedder: Embedder,
    qdrant_indexes: list[QdrantIndexSpec],
    bm25_index: Bm25Index,
    reranker: Reranker | None = None,
    top_k_fused: int = DEFAULT_TOP_K_FUSED,
    top_n: int = DEFAULT_TOP_N,
) -> list[RetrievedChunk]:
    """Run the full hybrid retrieval pipeline for a single query."""
    if not query.strip() or top_n <= 0:
        return []

    rankings: list[list[str]] = []
    chunks_by_key: dict[str, RagChunk] = {}

    def _dedup_key(chunk: RagChunk) -> str:
        # Phase 2: text + image collections can share `(doc_id, chunk_idx)`
        # (same PDF, same page index) so `chunk_id` alone is not unique
        # across collections. Tagging with `source_type` keeps text and
        # image chunks distinct in the RRF merge.
        return f"{chunk.source_type}::{chunk.chunk_id}"

    # Cache one query vector per distinct embedder — multimodal collections
    # use a different encoder than the text collection, but if multiple
    # collections share an embedder we encode the query just once.
    vec_by_embedder: dict[int, object] = {}

    def _encode(emb: Embedder) -> object:
        key = id(emb)
        if key not in vec_by_embedder:
            vec_by_embedder[key] = emb.encode([query])[0]
        return vec_by_embedder[key]

    for entry in qdrant_indexes:
        if isinstance(entry, tuple):
            qi, qi_embedder = entry
        else:
            qi, qi_embedder = entry, embedder
        query_vec = _encode(qi_embedder)
        dense_hits = qi.search(query_vec=query_vec, k=top_k_fused)  # type: ignore[arg-type]
        rankings.append([_dedup_key(chunk) for chunk, _ in dense_hits])
        for chunk, _ in dense_hits:
            chunks_by_key.setdefault(_dedup_key(chunk), chunk)

    sparse_hits = bm25_index.search(query, k=top_k_fused)
    rankings.append([_dedup_key(chunk) for chunk, _ in sparse_hits])
    for chunk, _ in sparse_hits:
        chunks_by_key.setdefault(_dedup_key(chunk), chunk)

    fused = rrf(rankings)[:top_k_fused]
    fused_chunks = [chunks_by_key[k] for k, _ in fused if k in chunks_by_key]

    if reranker is None:
        # Fall back to RRF score order. Match the API shape by wrapping in
        # RetrievedChunk; cap at top_n.
        return [
            RetrievedChunk(chunk=chunks_by_key[k], score=score)
            for k, score in fused[:top_n]
            if k in chunks_by_key
        ]

    return [
        RetrievedChunk(chunk=chunk, score=score)
        for chunk, score in reranker.rerank(query, fused_chunks, top_n=top_n)
    ]
