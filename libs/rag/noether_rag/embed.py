"""Text + multimodal embedders.

Phase 1 shipped `BgeTextEmbedder` (text only).  Phase 2 adds
`OpenClipEmbedder` covering both image and text in a single shared
embedding space — that's how text→image retrieval works without a
captioning hop. The earlier design called for a separate BGE-M3 path,
but BGE-M3 is text-only (see `design.md` errata), so the multimodal
path consolidates to OpenCLIP.

Both embedder classes satisfy the `Embedder` Protocol so they slot
into the existing `retrieve()` pipeline unchanged.
"""

from __future__ import annotations

import os
from typing import Final, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt
import open_clip
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer

DEFAULT_TEXT_MODEL: Final[str] = "BAAI/bge-base-en-v1.5"
DEFAULT_OPEN_CLIP_MODEL: Final[str] = "ViT-B-32"
DEFAULT_OPEN_CLIP_PRETRAINED: Final[str] = "laion2b_s34b_b79k"

FloatArray = npt.NDArray[np.float32]


@runtime_checkable
class Embedder(Protocol):
    """Anything that turns texts into dense vectors of a fixed dimension."""

    @property
    def dim(self) -> int: ...

    def encode(self, texts: list[str]) -> FloatArray: ...


@runtime_checkable
class ImageEmbedder(Protocol):
    """Anything that turns PIL images into dense vectors of a fixed dimension."""

    @property
    def dim(self) -> int: ...

    def encode_image(self, images: list[Image.Image]) -> FloatArray: ...


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


class OpenClipEmbedder:
    """OpenCLIP-backed multimodal embedder.

    Same instance encodes images (`encode_image`) and text (`encode_text`)
    into a shared L2-normalised embedding space — the design that enables
    cross-modal retrieval (text query → image hit) without a captioning
    hop. `encode` aliases `encode_text` so the class also satisfies the
    `Embedder` Protocol used by `retrieve()`.

    Args:
        model_name:  open_clip architecture name (default ViT-B-32).
        pretrained:  open_clip pretrained tag (default laion2b_s34b_b79k).
        cache_folder: where open_clip / huggingface_hub caches weights.
            Falls back to `RAG_MODEL_DIR` env var. Honored to make
            air-gapped runs work after a one-time warm.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_OPEN_CLIP_MODEL,
        pretrained: str = DEFAULT_OPEN_CLIP_PRETRAINED,
        cache_folder: str | None = None,
    ) -> None:
        cache = cache_folder if cache_folder is not None else os.getenv("RAG_MODEL_DIR")
        if cache is not None:
            # open_clip routes downloads through huggingface_hub; this is the
            # canonical knob.
            os.environ.setdefault("HF_HUB_CACHE", cache)

        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self._model = model.eval()
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(model_name)
        self._dim: int | None = None  # filled on first encode

    @property
    def dim(self) -> int:
        if self._dim is None:
            # Probe with a single text encode so we don't have to hardcode
            # the dim per architecture.
            self._encode_text_raw(["__dim_probe__"])
        assert self._dim is not None
        return self._dim

    def _encode_text_raw(self, texts: list[str]) -> FloatArray:
        tokens = self._tokenizer(texts)
        with torch.no_grad():
            feats = self._model.encode_text(tokens)
        feats = feats / (feats.norm(dim=-1, keepdim=True) + 1e-9)
        arr: FloatArray = feats.detach().cpu().numpy().astype(np.float32, copy=False)
        if self._dim is None:
            self._dim = int(arr.shape[1])
        return arr

    def encode_text(self, texts: list[str]) -> FloatArray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return self._encode_text_raw(texts)

    def encode_image(self, images: list[Image.Image]) -> FloatArray:
        if not images:
            return np.zeros((0, self.dim), dtype=np.float32)
        batch = torch.stack([self._preprocess(im) for im in images])
        with torch.no_grad():
            feats = self._model.encode_image(batch)
        feats = feats / (feats.norm(dim=-1, keepdim=True) + 1e-9)
        arr: FloatArray = feats.detach().cpu().numpy().astype(np.float32, copy=False)
        if self._dim is None:
            self._dim = int(arr.shape[1])
        return arr

    # `Embedder` Protocol conformance — text path is the natural alias.
    def encode(self, texts: list[str]) -> FloatArray:
        return self.encode_text(texts)
