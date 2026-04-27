## Why

The agent system needs a retrieval pipeline to ground answers in
documentation (NASA tech reports, DOE process safety docs) and on
P&ID images. SPEC §3 (6) makes RAG explicit. SPEC §4 (component 5)
locks in BGE embeddings, Qdrant, hybrid search with BM25, BGE
cross-encoder reranking, and RAGAS evaluation. SPEC §10 requires
RAGAS faithfulness, answer relevancy, and context precision in
`docs/benchmarks.md`.

This change is a Milestone 3 prerequisite (SPEC §8).

## What Changes

- Add `libs/rag/` with: PDF parsing, chunking, BGE embeddings, Qdrant
  client, hybrid search (vector + BM25), BGE cross-encoder reranker, and
  the RAGAS eval glue.
- Add an offline ingestion CLI that builds the index from a corpus
  directory.
- Add a thin retrieval service surface (callable from the agent) — no
  separate FastAPI service is needed at v0.1; the agent imports the lib.
- Add `eval/rag_ragas.py` running RAGAS faithfulness, answer relevancy,
  context precision against a fixed eval question set.
- Add Qdrant to `docker-compose.yml`.

## Capabilities

### New Capabilities
- `rag-pipeline`: Build, query, and evaluate a hybrid retrieval index over
  technical PDFs and image-bearing P&IDs, with BGE cross-encoder reranking.

### Modified Capabilities
_None._

## Impact

- New code: `libs/rag/`, `eval/rag_ragas.py`, ingestion CLI under
  `libs/rag/cli.py`.
- New deps (justified): `qdrant-client`, `sentence-transformers`
  (BGE base + BGE-M3 + reranker), `open-clip-torch` (OpenCLIP ViT-B/32
  for the image-only complement on the multimodal path), `rank-bm25`
  (lexical scorer), `pypdfium2` (PDF parsing — Apache 2 licence,
  preferred over PyMuPDF/AGPL), `ragas` (eval), `pillow` (image
  handling for P&IDs).
- New infra: Qdrant container in `docker-compose.yml`, persistent volume.
- Consumed by: agent system RAG and Multimodal RAG sub-agents.
- Out of scope: paid embedding APIs, custom embedding training,
  re-implementing chunkers (SPEC §9 + library discipline).
