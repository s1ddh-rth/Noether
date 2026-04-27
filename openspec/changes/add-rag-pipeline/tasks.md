## 1. Scaffolding

- [ ] 1.1 Create `libs/rag/` with `pyproject.toml` and `README.md`
- [ ] 1.2 Add Qdrant container to `docker-compose.yml` with persistent
      volume + healthcheck
- [ ] 1.3 Pin `qdrant-client`, `sentence-transformers`,
      `open-clip-torch`, `rank-bm25`, `pypdfium2`, `ragas`, `pillow`

## 2. Document parsing and chunking

- [ ] 2.1 PDF text extraction via `pypdfium2`
- [ ] 2.2 Image extraction for P&IDs
- [ ] 2.3 Recursive character chunker (~500 tokens, 50 token overlap)
- [ ] 2.4 Document model: `RagChunk { doc_id, source_type, chunk_idx,
      text, metadata }`

## 3. Embeddings and indexing

- [ ] 3.1 BGE-base-en-v1.5 default loader; BGE-M3 selectable via env
- [ ] 3.2 Qdrant collection bootstrap with vector + payload schema
- [ ] 3.3 Bulk upsert via `qdrant_client.upload_points`
- [ ] 3.4 BM25 corpus pickled to `_bm25.pkl` next to Qdrant data

## 4. Multimodal

- [ ] 4.1 BGE-M3 multimodal embedder (`sentence-transformers` with the
      BGE-M3 image-text mode); collection `noether_mm_bge` in Qdrant
- [ ] 4.2 OpenCLIP ViT-B/32 image embedder; collection
      `noether_mm_clip` in Qdrant
- [ ] 4.3 Same `RagChunk` shape with `source_type="pid_image"` payload;
      both collections share the same payload fields keyed by `doc_id`
- [ ] 4.4 Multimodal retrieve path: query both collections, RRF merge,
      then unified reranker step against text view of nearest chunks
- [ ] 4.5 Models pre-baked into the ingestion image for air-gap warm

## 5. Retrieval

- [ ] 5.1 `retrieve(query, k)` performs dense + BM25, RRF fusion
- [ ] 5.2 Reranker step on fused top-20 with BGE-reranker-base
- [ ] 5.3 Returns top-k `RagChunk`s with score

## 6. Ingestion CLI

- [ ] 6.1 `python -m libs.rag.cli ingest --src DIR --collection NAME`
- [ ] 6.2 Idempotent: re-running is a no-op for unchanged docs (hash on
      file content)

## 7. Eval harness

- [ ] 7.1 `eval/rag_ragas.py` consumes
      `eval/data/rag_eval_questions.jsonl`
- [ ] 7.2 Computes faithfulness / answer_relevancy / context_precision
- [ ] 7.3 Writes `eval/results/rag.json`
- [ ] 7.4 Renders Markdown table into `docs/benchmarks.md`

## 8. Tests

- [ ] 8.1 Unit: chunker boundary cases (short doc, very long doc)
- [ ] 8.2 Unit: RRF fusion correctness against a hand-built example
- [ ] 8.3 Integration: ingest 3-doc fixture, retrieve, assert top hit
- [ ] 8.4 Multimodal: P&ID with `FT-101` label retrievable by name
- [ ] 8.5 Coverage >=70% on `libs/rag/`

## 9. Air-gap

- [ ] 9.1 Models cached locally; no Hub downloads at runtime under
      `OFFLINE_MODE=1`
- [ ] 9.2 Document warm-up step in service README

## 10. Eval / Benchmarks

- [ ] 10.1 First RAG benchmarks committed to `docs/benchmarks.md`
- [ ] 10.2 CI re-runs RAGAS on PRs touching `libs/rag/`

## 11. Docs

- [ ] 11.1 `libs/rag/README.md`: ingest CLI, retrieve API, env vars
- [ ] 11.2 RAG section added to `docs/architecture.md`
