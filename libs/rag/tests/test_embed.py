from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import numpy.typing as npt
from noether_rag.embed import BgeTextEmbedder, Embedder


class StubEmbedder:
    """Deterministic test embedder; structural conformance to `Embedder`."""

    dim = 4

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        # one-hot-ish: hash(text) mod dim → one-hot vector
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            out[i, hash(t) % self.dim] = 1.0
        return out


def test_stub_satisfies_embedder_protocol() -> None:
    e: Embedder = StubEmbedder()
    vecs = e.encode(["a", "b"])
    assert vecs.shape == (2, 4)
    assert vecs.dtype == np.float32
    assert e.dim == 4


def test_bge_text_embedder_uses_sentence_transformers_with_cache() -> None:
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 768
    fake_model.encode.return_value = np.zeros((2, 768), dtype=np.float32)

    with patch("noether_rag.embed.SentenceTransformer", return_value=fake_model) as m:
        emb = BgeTextEmbedder(model_name="BAAI/bge-base-en-v1.5", cache_folder="/tmp/m")
        m.assert_called_once_with("BAAI/bge-base-en-v1.5", cache_folder="/tmp/m")
        assert emb.dim == 768

        out = emb.encode(["hello", "world"])
        assert out.shape == (2, 768)
        # calls underlying model.encode with the input list and asks for ndarray
        kwargs: dict[str, Any] = fake_model.encode.call_args.kwargs
        assert kwargs.get("convert_to_numpy") is True
        assert kwargs.get("normalize_embeddings") is True


def test_bge_text_embedder_default_model_matches_spec() -> None:
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 768
    with patch("noether_rag.embed.SentenceTransformer", return_value=fake_model) as m:
        BgeTextEmbedder()
        # default should be the BGE base model named in the proposal
        assert m.call_args.args[0] == "BAAI/bge-base-en-v1.5"


def test_encode_empty_list_returns_empty_array() -> None:
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 768
    fake_model.encode.return_value = np.zeros((0, 768), dtype=np.float32)
    with patch("noether_rag.embed.SentenceTransformer", return_value=fake_model):
        emb = BgeTextEmbedder()
        out = emb.encode([])
        assert out.shape == (0, 768)
        # underlying model.encode should NOT be called for empty input
        fake_model.encode.assert_not_called()
