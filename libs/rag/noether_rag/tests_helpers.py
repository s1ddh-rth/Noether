"""Test-only helpers shared between unit and integration tests.

These are imported by tests inside `libs/rag/tests/` and by the agent
service's RAG-tool tests in Phase 2. Keeping them in the package (not in
`tests/`) makes them importable across packages without copy-paste.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float32]


class StubTextEmbedder:
    """Deterministic dense embedder for tests.

    Vectors are derived from a hash of each text so identical strings
    produce identical vectors — useful for "ingest then retrieve same
    string" tests without needing a real BGE model loaded.
    """

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> FloatArray:
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, t in enumerate(texts):
            seed = abs(hash(t)) % (2**32)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self._dim).astype(np.float32)
            # L2-normalise to make cosine sim well-behaved.
            v /= np.linalg.norm(v) + 1e-9
            out[i] = v
        return out
