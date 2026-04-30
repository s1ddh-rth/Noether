from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import torch
from noether_rag.embed import OpenClipEmbedder
from PIL import Image


def _make_fake_open_clip(dim: int = 512) -> tuple[MagicMock, MagicMock]:
    """Build mocks that mimic the open_clip surface we touch."""
    model = MagicMock()

    def _encode_text(tokens: torch.Tensor) -> torch.Tensor:
        n = int(tokens.shape[0])
        return torch.ones((n, dim), dtype=torch.float32) * 0.5

    def _encode_image(image_tensor: torch.Tensor) -> torch.Tensor:
        n = int(image_tensor.shape[0])
        return torch.ones((n, dim), dtype=torch.float32) * 0.3

    model.encode_text.side_effect = _encode_text
    model.encode_image.side_effect = _encode_image
    model.eval = MagicMock(return_value=model)

    preprocess = MagicMock(side_effect=lambda im: torch.zeros((3, 224, 224), dtype=torch.float32))
    tokenizer = MagicMock(side_effect=lambda txts: torch.zeros((len(txts), 77), dtype=torch.long))

    create_fn = MagicMock(return_value=(model, None, preprocess))
    get_tokenizer = MagicMock(return_value=tokenizer)
    return create_fn, get_tokenizer


class TestOpenClipEmbedderConstruction:
    def test_default_model_is_vit_b_32(self) -> None:
        create_fn, get_tok = _make_fake_open_clip()
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            OpenClipEmbedder()
            assert create_fn.call_args.args[0] == "ViT-B-32"

    def test_dim_is_taken_from_model_output(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            assert emb.dim == 512


class TestEncodeText:
    def test_returns_float32_2d_array(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode_text(["hello", "world", "FT-101"])
            assert out.shape == (3, 512)
            assert out.dtype == np.float32

    def test_outputs_l2_normalised(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=8)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode_text(["a"])
            norm = float(np.linalg.norm(out[0]))
            assert abs(norm - 1.0) < 1e-5

    def test_empty_input_returns_empty_array(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode_text([])
            assert out.shape == (0, 512)


class TestEncodeImage:
    def test_returns_float32_2d_array(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            imgs = [Image.new("RGB", (10, 10)) for _ in range(2)]
            out = emb.encode_image(imgs)
            assert out.shape == (2, 512)
            assert out.dtype == np.float32

    def test_outputs_l2_normalised(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=8)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode_image([Image.new("RGB", (10, 10))])
            norm = float(np.linalg.norm(out[0]))
            assert abs(norm - 1.0) < 1e-5

    def test_empty_input_returns_empty_array(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode_image([])
            assert out.shape == (0, 512)


class TestEmbedderProtocolForText:
    """`encode` (text) on OpenClipEmbedder satisfies the `Embedder` Protocol
    so callers can drop it into the existing `retrieve()` pipeline for
    cross-modal text→image queries."""

    def test_encode_alias_dispatches_to_encode_text(self) -> None:
        create_fn, get_tok = _make_fake_open_clip(dim=512)
        with patch("noether_rag.embed.open_clip") as oc:
            oc.create_model_and_transforms = create_fn
            oc.get_tokenizer = get_tok
            emb = OpenClipEmbedder()
            out = emb.encode(["hello"])
            assert out.shape == (1, 512)
