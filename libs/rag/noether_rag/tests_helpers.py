"""Test-only helpers shared between unit and integration tests.

These are imported by tests inside `libs/rag/tests/`, by `eval/tests/`,
and by the agent service's RAG-tool tests in Phase 2. Keeping them in
the package (not in `tests/`) makes them importable across packages
without copy-paste.
"""

from __future__ import annotations

import base64

import numpy as np
import numpy.typing as npt
from PIL import Image

FloatArray = npt.NDArray[np.float32]


# 1953-byte 2-page PDF, frozen here so tests don't depend on docker, on
# network downloads, or on a third-party PDF generator at runtime. Page 1
# mentions "FT-101"; page 2 mentions "Steam pressure". Regenerated once
# locally with reportlab.
_SAMPLE_PDF_B64 = (
    "JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3Vy"
    "Y2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAv"
    "SGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAv"
    "VHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDggMCBSIC9N"
    "ZWRpYUJveCBbIDAgMCA1OTUuMjc1NiA4NDEuODg5OCBdIC9QYXJlbnQgNyAwIFIgL1Jlc291cmNl"
    "cyA8PAovRm9udCAxIDAgUiAvUHJvY1NldCBbIC9QREYgL1RleHQgL0ltYWdlQiAvSW1hZ2VDIC9J"
    "bWFnZUkgXQo+PiAvUm90YXRlIDAgL1RyYW5zIDw8Cgo+PiAKICAvVHlwZSAvUGFnZQo+PgplbmRv"
    "YmoKNCAwIG9iago8PAovQ29udGVudHMgOSAwIFIgL01lZGlhQm94IFsgMCAwIDU5NS4yNzU2IDg0"
    "MS44ODk4IF0gL1BhcmVudCA3IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250IDEgMCBSIC9Qcm9jU2V0"
    "IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+IC9Sb3RhdGUgMCAvVHJh"
    "bnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9QYWdlTW9kZSAv"
    "VXNlTm9uZSAvUGFnZXMgNyAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjYgMCBvYmoKPDwK"
    "L0F1dGhvciAoYW5vbnltb3VzKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYwNDI5MTM0OTI4KzAxJzAw"
    "JykgL0NyZWF0b3IgKGFub255bW91cykgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjYwNDI5"
    "MTM0OTI4KzAxJzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSBcKG9wZW5z"
    "b3VyY2VcKSkgCiAgL1N1YmplY3QgKHVuc3BlY2lmaWVkKSAvVGl0bGUgKHVudGl0bGVkKSAvVHJh"
    "cHBlZCAvRmFsc2UKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NvdW50IDIgL0tpZHMgWyAzIDAgUiA0"
    "IDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOCAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJ"
    "ODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCAxODAKPj4Kc3RyZWFtCkdhclcwWW4iVykm"
    "ND8yQEtoIkQmakBVX0FVaDQpSysiM3Q+UFU6cjxUdG85JFdZY1M3L0olUjIsOkYvS2ZpVlkuZk90"
    "PSRpIXJgSy0yPCJKMVs0Lk5cZ3RdK0NwRG5rTWdJNSgoISM1W0xYJi0zLVtRZmsrKU85LUgpVFVS"
    "U0dZQlNKcFsiUCVucjZFOUZsUz0lKC4lVk0sRStlWT1UPWJjbEEzKSZfZ1kiWjRGKHExJDh+PmVu"
    "ZHN0cmVhbQplbmRvYmoKOSAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRl"
    "RGVjb2RlIF0gL0xlbmd0aCAxODEKPj4Kc3RyZWFtCkdhcldwXyRcJTUmLVVALF5MRTNRKHBjKEJH"
    "U0tMOTppTG5sQyJLKWU4UCxdVUk3KlBfNiRDbnUwS2FzMzgrV3AyaTUhdUUiPWg1SE8+QEFvX05C"
    "YzNkcyZBUkYiRmlBaVpiS0s5YF1EKzhVV0EoLUMjVz5lOF1rKTcxPnFYO083JTxlaCJXSm5FUSdJ"
    "aDxeWztOS1FWXWU9QC0hO2skZixdXkxIMGY0PSxJNWsra0UzXF5nfj5lbmRzdHJlYW0KZW5kb2Jq"
    "CnhyZWYKMCAxMAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwNjEgMDAwMDAgbiAKMDAwMDAw"
    "MDA5MiAwMDAwMCBuIAowMDAwMDAwMTk5IDAwMDAwIG4gCjAwMDAwMDA0MDIgMDAwMDAgbiAKMDAw"
    "MDAwMDYwNSAwMDAwMCBuIAowMDAwMDAwNjczIDAwMDAwIG4gCjAwMDAwMDA5MzQgMDAwMDAgbiAK"
    "MDAwMDAwMDk5OSAwMDAwMCBuIAowMDAwMDAxMjY5IDAwMDAwIG4gCnRyYWlsZXIKPDwKL0lEIApb"
    "PDIxYTczZDFhMmIzNTA2MjQ4ODc1NGRhZTE5MWI0OWIxPjwyMWE3M2QxYTJiMzUwNjI0ODg3NTRk"
    "YWUxOTFiNDliMT5dCiUgUmVwb3J0TGFiIGdlbmVyYXRlZCBQREYgZG9jdW1lbnQgLS0gZGlnZXN0"
    "IChvcGVuc291cmNlKQoKL0luZm8gNiAwIFIKL1Jvb3QgNSAwIFIKL1NpemUgMTAKPj4Kc3RhcnR4"
    "cmVmCjE1NDAKJSVFT0YK"
)


def sample_pdf_bytes() -> bytes:
    """Decoded bytes of the embedded 2-page test PDF."""
    return base64.b64decode(_SAMPLE_PDF_B64)


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


class StubImageEmbedder:
    """Deterministic image embedder for tests.

    Vectors are derived from the image's mean pixel value so that two
    visually-similar images produce close vectors. Useful for end-to-end
    multimodal ingest tests without loading OpenCLIP weights.
    """

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode_image(self, images: list[Image.Image]) -> FloatArray:
        if not images:
            return np.zeros((0, self._dim), dtype=np.float32)
        out = np.zeros((len(images), self._dim), dtype=np.float32)
        for i, im in enumerate(images):
            grey = im.convert("L").resize((4, 4))
            seed = sum(grey.getdata()) % (2**32)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self._dim).astype(np.float32)
            v /= np.linalg.norm(v) + 1e-9
            out[i] = v
        return out
