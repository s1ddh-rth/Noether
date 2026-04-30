"""Qdrant + BM25 index wrappers.

`QdrantIndex` is the dense vector side; `Bm25Index` is the sparse side.
Both are designed to be exercised in tests via in-memory or in-process
backends so the unit suite never needs docker.
"""

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from rank_bm25 import BM25Okapi

from noether_rag.models import RagChunk

FloatArray = npt.NDArray[np.float32]

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Lowercase word-tokenizer used for BM25 indexing and querying."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


class QdrantIndex:
    """Thin wrapper around a `QdrantClient` collection.

    The wrapper owns nothing beyond a client reference and the collection
    name; callers can hand in `QdrantClient(":memory:")` for tests or a
    URL-based client for real deployments without changing this class.
    """

    def __init__(self, client: QdrantClient, collection: str) -> None:
        self.client = client
        self.collection = collection

    def ensure_collection(self, dim: int) -> None:
        """Create the collection at the given dimension if it does not exist."""
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(
                size=dim,
                distance=qmodels.Distance.COSINE,
            ),
        )

    def upsert(self, chunks: list[RagChunk], vectors: FloatArray) -> None:
        """Idempotent upsert — point IDs are derived from `(doc_id, chunk_idx)`."""
        if not chunks and vectors.shape[0] == 0:
            return
        if len(chunks) != vectors.shape[0]:
            raise ValueError(
                f"chunks/vectors length mismatch: "
                f"{len(chunks)} chunks vs {vectors.shape[0]} vectors"
            )
        points = [
            qmodels.PointStruct(
                id=chunk.point_uuid,
                vector=vectors[i].tolist(),
                payload=chunk.model_dump(),
            )
            for i, chunk in enumerate(chunks)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_vec: FloatArray,
        k: int,
    ) -> list[tuple[RagChunk, float]]:
        """Return the top-k `(chunk, similarity)` pairs."""
        hits = self.client.query_points(
            collection_name=self.collection,
            query=query_vec.tolist(),
            limit=k,
            with_payload=True,
        ).points
        out: list[tuple[RagChunk, float]] = []
        for h in hits:
            payload: dict[str, Any] = dict(h.payload or {})
            out.append((RagChunk.model_validate(payload), float(h.score)))
        return out

    def count(self) -> int:
        """Exact point count — useful for tests."""
        return int(self.client.count(collection_name=self.collection, exact=True).count)

    def known_doc_ids(self) -> set[str]:
        """Walk every point in the collection and return distinct `doc_id`s.

        Used by the multimodal ingest path for cross-run dedup; the
        text-side ingest gets the same effect for free via the BM25
        pickle. Safe to call before the collection exists — returns an
        empty set in that case.
        """
        if not self.client.collection_exists(self.collection):
            return set()
        out: set[str] = set()
        next_offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection,
                limit=512,
                with_payload=True,
                offset=next_offset,
            )
            for p in points:
                payload = p.payload or {}
                doc_id = payload.get("doc_id")
                if isinstance(doc_id, str):
                    out.add(doc_id)
            if next_offset is None:
                break
        return out


class Bm25Index:
    """In-memory BM25 sparse retriever, picklable to disk for ingest reuse.

    `fit(chunks)` builds the index. `search(query, k)` returns the top-k
    `(chunk, score)` pairs. `save(path)` / `load(path)` round-trip the
    fitted index via `pickle` — re-fitting on every service start is fine
    for the corpus sizes targeted by v0.1, but pickling lets the ingestion
    CLI's work survive a service restart without re-walking the docs.
    """

    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._chunks: list[RagChunk] = []

    def fit(self, chunks: list[RagChunk]) -> None:
        self._chunks = list(chunks)
        if not self._chunks:
            self._bm25 = None
            return
        tokenized = [_tokenize(c.text) for c in self._chunks]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, k: int) -> list[tuple[RagChunk, float]]:
        if self._bm25 is None or not self._chunks:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        # Argsort descending; cap at k.
        order = np.argsort(-scores)[:k]
        return [(self._chunks[int(i)], float(scores[int(i)])) for i in order]

    def save(self, path: str | Path) -> None:
        with Path(path).open("wb") as fh:
            pickle.dump({"chunks": self._chunks, "bm25": self._bm25}, fh)

    @classmethod
    def load(cls, path: str | Path) -> Bm25Index:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        with p.open("rb") as fh:
            payload = pickle.load(fh)
        idx = cls()
        idx._chunks = payload["chunks"]
        idx._bm25 = payload["bm25"]
        return idx
