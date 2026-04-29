# noether-rag

Hybrid retrieval over technical PDFs.

| Stage | Backed by | Notes |
|---|---|---|
| PDF text extraction | `pypdfium2` (Apache-2) | per-page text; preserved for chunk metadata |
| Chunking | hand-rolled recursive char splitter | ~500 chars, 50 overlap; standalone (no LangChain dep) |
| Dense embedding | `sentence-transformers` BAAI/bge-base-en-v1.5 | 768-dim; cached under `MODEL_DIR` for air-gap |
| Vector index | Qdrant | one collection per embedding model |
| Sparse retrieval | `rank-bm25` | corpus pickled to `_bm25.pkl` next to the Qdrant data |
| Fusion | reciprocal rank fusion, k=60 | reused unchanged for multimodal merge in Phase 2 |
| Reranker | `sentence-transformers` BAAI/bge-reranker-base | top-K=20 → top-N=5 |

> **Phase 1 scope (this README).** Text-only ingestion + retrieval through
> the four-stage pipeline above. Phase 2 (a follow-up PR on the same
> OpenSpec change `add-rag-pipeline`) adds multimodal P&ID embedding
> (BGE-M3 + OpenCLIP), the RAGAS eval harness, and the air-gap warm-up
> script. The Phase-1 surfaces (`Embedder` Protocol, `QdrantIndex`,
> `rrf`, `retrieve`) are designed so Phase 2 plugs in without touching
> them.

## Public API

```python
from noether_rag import (
    BgeTextEmbedder,
    BgeReranker,
    Bm25Index,
    QdrantIndex,
    RagChunk,
    chunk_text,
    extract_text,
    retrieve,
    rrf,
)
```

## Ingest CLI

```bash
python -m noether_rag.cli ingest \
    --src ./data/rag-corpus \
    --collection noether_text
```

Idempotent: documents are keyed by SHA-256 of file content, so re-running
is a no-op for unchanged files.

## Env vars

| Var | Default | Purpose |
|---|---|---|
| `RAG_QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `RAG_MODEL_DIR` | `./models/rag` | sentence-transformers cache root |
| `RAG_TEXT_EMBEDDER` | `BAAI/bge-base-en-v1.5` | dense text model |
| `RAG_RERANKER` | `BAAI/bge-reranker-base` | cross-encoder |
| `RAG_DATA_DIR` | `./data/rag-index` | BM25 pickle location |
| `HF_HUB_CACHE` | `$RAG_MODEL_DIR` if set | OpenCLIP weight cache (set by `OpenClipEmbedder`) |

## Multimodal (P&IDs)

`OpenClipEmbedder` covers both `encode_image(list[PIL.Image])` and
`encode_text(list[str])` in the same shared embedding space. Ingest
PDFs as page-rendered images:

```python
from qdrant_client import QdrantClient
from noether_rag import OpenClipEmbedder, QdrantIndex
from noether_rag.ingest import ingest_dir_multimodal

embedder = OpenClipEmbedder()
mm_idx = QdrantIndex(QdrantClient(url="http://localhost:6333"), "noether_mm_clip")
ingest_dir_multimodal(src=pdf_dir, qdrant_index=mm_idx, image_embedder=embedder)
```

For cross-modal retrieval, pass the multimodal index with its own
embedder when calling `retrieve()`:

```python
retrieve(
    "FT-101",
    embedder=text_embedder,                 # default for plain entries
    qdrant_indexes=[
        text_idx,                           # uses default `embedder`
        (mm_idx, mm_embedder),              # uses OpenCLIP text encoder
    ],
    bm25_index=bm,
)
```

## Air-gap warm-up

After a one-time online warm, `RAG_MODEL_DIR` (and `HF_HUB_CACHE`)
contain every weight needed for offline operation. Run this once
against the network:

```bash
RAG_MODEL_DIR=./models/rag uv run python -c "
from noether_rag import BgeTextEmbedder, BgeReranker, OpenClipEmbedder
BgeTextEmbedder()        # ~440 MB — BAAI/bge-base-en-v1.5
BgeReranker()            # ~280 MB — BAAI/bge-reranker-base
OpenClipEmbedder()       # ~600 MB — ViT-B-32 / laion2b_s34b_b79k
print('warm cache ready in', __import__('os').environ['RAG_MODEL_DIR'])
"
```

After that, set `OFFLINE_MODE=1` and the embedders read from cache only;
no DNS, no Hub calls.

## Tests

```
uv run pytest libs/rag
```

Unit tests use Qdrant's in-memory client (`QdrantClient(":memory:")`),
a stub `Embedder`, and a mocked OpenCLIP, so they don't need docker or
model downloads.
