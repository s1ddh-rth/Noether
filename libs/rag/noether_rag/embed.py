"""Text embedders.

Phase 1 ships `BgeTextEmbedder` only. Phase 2 will add `BgeM3Embedder`
(text + image dense) and `OpenClipImageEmbedder` (image-only complement)
behind the same `Embedder` Protocol; downstream code never imports a
specific implementation, so adding them is non-breaking.
"""

from __future__ import annotations

import os
from typing import Final, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
from sentence_transformers import SentenceTransformer

DEFAULT_TEXT_MODEL: Final[str] = "BAAI/bge-base-en-v1.5"

FloatArray = npt.NDArray[np.float32]


@runtime_checkable
class Embedder(Protocol):
    """Anything that turns texts into dense vectors of a fixed dimension."""

    @property
    def dim(self) -> int: ...

    def encode(self, texts: list[str]) -> FloatArray: ...


class BgeTextEmbedder:
    """Sentence-transformers-backed dense text embedder.

    Args:
        model_name: HuggingFace model id; defaults to BGE-base-en-v1.5.
        cache_folder: where sentence-transformers caches model weights.
            Falls back to `RAG_MODEL_DIR` env var if unset, then to the
            sentence-transformers default. Honored to make air-gapped
            runs work after a one-time warm.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_TEXT_MODEL,
        cache_folder: str | None = None,
    ) -> None:
        cache = cache_folder if cache_folder is not None else os.getenv("RAG_MODEL_DIR")
        self._model = SentenceTransformer(model_name, cache_folder=cache)
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:  # pragma: no cover — sentence-transformers always returns a dim
            raise RuntimeError(f"sentence-transformers model {model_name!r} reported no dimension")
        self._dim = int(dim)

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> FloatArray:
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        out = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(out, dtype=np.float32)
