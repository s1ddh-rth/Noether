"""Cross-encoder reranker.

Uses `sentence_transformers.CrossEncoder` to score (query, chunk.text)
pairs. The default model `BAAI/bge-reranker-base` is the one named in
the `add-rag-pipeline` design doc; cache_folder is honored so the model
materialises in `RAG_MODEL_DIR` for air-gap warmup.
"""

from __future__ import annotations

import os
from typing import Final, Protocol, runtime_checkable

import numpy as np
from sentence_transformers import CrossEncoder

from noether_rag.models import RagChunk

DEFAULT_RERANKER: Final[str] = "BAAI/bge-reranker-base"


@runtime_checkable
class Reranker(Protocol):
    def rerank(
        self, query: str, chunks: list[RagChunk], top_n: int
    ) -> list[tuple[RagChunk, float]]: ...


class BgeReranker:
    """BAAI/bge-reranker-base via sentence-transformers CrossEncoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER,
        cache_folder: str | None = None,
    ) -> None:
        cache = cache_folder if cache_folder is not None else os.getenv("RAG_MODEL_DIR")
        # sentence-transformers exposes `cache_dir` on CrossEncoder (not
        # `cache_folder` like SentenceTransformer); kwarg name normalised
        # here. CrossEncoder's stub doesn't accept None, so we only pass
        # the kwarg when the user supplied one.
        if cache is None:
            self._model = CrossEncoder(model_name)
        else:
            self._model = CrossEncoder(model_name, cache_dir=cache)

    def rerank(
        self, query: str, chunks: list[RagChunk], top_n: int
    ) -> list[tuple[RagChunk, float]]:
        if not chunks:
            return []
        pairs = [(query, c.text) for c in chunks]
        scores = np.asarray(self._model.predict(pairs), dtype=np.float32)
        order = np.argsort(-scores)[:top_n]
        return [(chunks[int(i)], float(scores[int(i)])) for i in order]
