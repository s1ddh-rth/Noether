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

## Tests

```
uv run pytest libs/rag
```

Unit tests use Qdrant's in-memory client (`QdrantClient(":memory:")`) and
a stub `Embedder` so they don't need docker or model downloads.
