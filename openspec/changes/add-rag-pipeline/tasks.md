## 1. Scaffolding

- [x] 1.1 Create `libs/rag/` with `pyproject.toml` and `README.md`
- [x] 1.2 Add Qdrant container to `docker-compose.yml` with persistent
      volume + healthcheck
      - shipped without a healthcheck; the official Qdrant image is
        distroless-ish (no curl/wget/python/bash). The agent service in
        the next change will add an SDK-based readiness probe from a
        depending container.
- [x] 1.3 Pin `qdrant-client`, `sentence-transformers`,
      `open-clip-torch`, `rank-bm25`, `pypdfium2`, `ragas`, `pillow`
      *(Phase 2 appended `open-clip-torch`, `pillow`, `ragas`.)*

## 2. Document parsing and chunking

- [x] 2.1 PDF text extraction via `pypdfium2`
- [x] 2.2 Image extraction for P&IDs
      *(Phase 2: `extract_page_images(path, dpi)` renders each page to a
      PIL Image. P&IDs delivered as PDFs are typically one diagram per
      page, so page-render is the right granularity.)*
- [x] 2.3 Recursive character chunker (~500 tokens, 50 token overlap)
- [x] 2.4 Document model: `RagChunk { doc_id, source_type, chunk_idx,
      text, metadata }`

## 3. Embeddings and indexing

- [x] 3.1 BGE-base-en-v1.5 default loader; BGE-M3 selectable via env
      *(BGE-base shipped Phase 1. BGE-M3 path dropped in Phase 2 — see
      `design.md` Errata: BGE-M3 is text-only and the multimodal arm
      consolidates to OpenCLIP. BGE-M3 as an alternative *text* encoder
      is a future option but not part of this change.)*
- [x] 3.2 Qdrant collection bootstrap with vector + payload schema
- [x] 3.3 Bulk upsert via `qdrant_client.upload_points`
      *(implemented via `client.upsert(points=...)` — equivalent for our
      payload-bearing case and idempotent via stable point UUIDs)*
- [x] 3.4 BM25 corpus pickled to `_bm25.pkl` next to Qdrant data

## 4. Multimodal

- [x] 4.1 BGE-M3 multimodal embedder
      *(Dropped — BGE-M3 has no image branch; see `design.md` Errata.
      The multimodal text+image arm consolidates to OpenCLIP only.)*
- [x] 4.2 OpenCLIP ViT-B/32 image embedder; collection
      `noether_mm_clip` in Qdrant
      *(Phase 2: `OpenClipEmbedder` covers both `encode_image` and
      `encode_text` in the shared embedding space.)*
- [x] 4.3 Same `RagChunk` shape with `source_type="pid_image"` payload;
      both collections share the same payload fields keyed by `doc_id`
- [x] 4.4 Multimodal retrieve path: query both collections, RRF merge,
      then unified reranker step against text view of nearest chunks
      *(Phase 2: `retrieve()` accepts per-collection embedders via
      `list[QdrantIndex | tuple[QdrantIndex, Embedder]]`; dedup key
      includes `source_type` so text and image chunks don't shadow each
      other.)*
- [ ] 4.5 Models pre-baked into the ingestion image for air-gap warm
      *(Documented in `libs/rag/README.md` warm-up section; the actual
      pre-baking lives with the M3 agent service Dockerfile.)*

## 5. Retrieval

- [x] 5.1 `retrieve(query, k)` performs dense + BM25, RRF fusion
- [x] 5.2 Reranker step on fused top-20 with BGE-reranker-base
- [x] 5.3 Returns top-k `RagChunk`s with score

## 6. Ingestion CLI

- [x] 6.1 `python -m libs.rag.cli ingest --src DIR --collection NAME`
      *(installed as `python -m noether_rag.cli ingest ...` — the
      package name is `noether_rag` per workspace convention)*
- [x] 6.2 Idempotent: re-running is a no-op for unchanged docs (hash on
      file content)

## 7. Eval harness

- [x] 7.1 `eval/rag_ragas.py` consumes
      `eval/data/rag_eval_questions.jsonl`
- [~] 7.2 Computes faithfulness / answer_relevancy / context_precision
      *(Phase 2 ships retrieval-only hit-rate; the LLM-dependent RAGAS
      metrics require the agent service's LLM provider abstraction and
      land with `add-agent-system`. The harness plumbing is designed to
      plug LLM scorers in unchanged.)*
- [x] 7.3 Writes `eval/results/rag.json`
- [x] 7.4 Renders Markdown table into `docs/benchmarks.md`

## 8. Tests

- [x] 8.1 Unit: chunker boundary cases (short doc, very long doc)
- [x] 8.2 Unit: RRF fusion correctness against a hand-built example
- [x] 8.3 Integration: ingest 3-doc fixture, retrieve, assert top hit
- [x] 8.4 Multimodal: P&ID with `FT-101` label retrievable by name
      *(Phase 2: `test_retrieve_multimodal.py` — text query surfaces a
      P&ID image hit via OpenCLIP cross-modal text encoder + RRF merge.)*
- [x] 8.5 Coverage >=70% on `libs/rag/`

## 9. Air-gap

- [x] 9.1 Models cached locally; no Hub downloads at runtime under
      `OFFLINE_MODE=1`
- [x] 9.2 Document warm-up step in service README
      *(Phase 2: `libs/rag/README.md` warm-up section.)*

## 10. Eval / Benchmarks

- [x] 10.1 First RAG benchmarks committed to `docs/benchmarks.md`
      *(retrieval hit-rate; LLM-dependent RAGAS scores follow the
      agent-service change.)*
- [ ] 10.2 CI re-runs RAGAS on PRs touching `libs/rag/`
      *(deferred — wired up alongside 7.2 once the LLM lands.)*

## 11. Docs

- [x] 11.1 `libs/rag/README.md`: ingest CLI, retrieve API, env vars
- [x] 11.2 RAG section added to `docs/architecture.md`
