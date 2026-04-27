## Context

Two retrieval surfaces matter at v0.1:
1. Text RAG over the public corpus (NASA + DOE).
2. Multimodal RAG over self-generated P&IDs (drawio).

Both can share the same Qdrant index and embedding pipeline if we treat
P&IDs as image-with-caption documents. SPEC §6 names BGE-base / BGE-M3
for embeddings and BGE-reranker-base for cross-encoding.

## Goals / Non-Goals

**Goals:**
- One ingestion CLI that handles PDFs and P&ID images uniformly.
- Hybrid search: dense Qdrant similarity + BM25 sparse, fused via
  reciprocal rank fusion (RRF).
- Reranking with BGE-reranker-base on top-K (K=20).
- RAGAS eval against a fixed question set in
  `eval/data/rag_eval_questions.jsonl`.
- All BGE models cached locally; air-gapped runs work after one-time
  warm.

**Non-Goals (per SPEC §9):**
- Custom embedding training.
- Paid embedding APIs in default config.
- Continual indexing or live-document ingestion (batch only at v0.1).

## Decisions

- **PDF parser:** `pymupdf` for text + image extraction; faster and
  more accurate than `pypdf`. Licence: AGPL — acceptable for our Apache
  2.0 repo because PyMuPDF is consumed only as a build-time tool inside
  ingestion; alternative: `pypdfium2` (Apache 2). Final pick: `pypdfium2`
  to keep license cleanliness.
- **Chunker:** `LangChain`'s `RecursiveCharacterTextSplitter` analogue
  re-implemented as a 30-line function (we already pull LangChain via
  LangGraph in the agent change, but isolating chunker keeps `libs/rag/`
  independent of LangChain).
- **Embeddings:** BGE-base-en-v1.5 by default; BGE-M3 selectable via env.
  Both via `sentence-transformers`.
- **Vector store:** Qdrant. Single collection per language model with
  payload index on `doc_id` and `source_type`.
- **Sparse:** `rank-bm25` over the same chunk text, indexed in memory at
  service start.
- **Fusion:** Reciprocal Rank Fusion with k=60.
- **Reranker:** BGE-reranker-base on top-K=20, output top-N=5.
- **Multimodal:** P&ID images are embedded directly — no captioning
  hop. We use BGE-M3 (text + image dense) for the unified embedding
  space and OpenCLIP (`open-clip-torch`, ViT-B/32 by default) as the
  image-only complement to catch visual-only signal. Each P&ID is
  embedded with both models and stored in two parallel Qdrant
  collections; retrieval queries each and merges via the same RRF used
  for text. We rejected BLIP-2 captioning because:
    1. P&ID retrieval is fundamentally an embedding problem (find the
       diagram for a tag/unit), not a captioning one — captioning adds
       a lossy summarisation step that loses spatial context.
    2. Embedding-only keeps the multimodal path consistent with the
       text RAG path (same Qdrant, same RRF, same reranker semantics),
       so there is one mental model to debug.
    3. BLIP-2 weights are large (~7 GB) and slow to warm; BGE-M3
       (~570 MB) and OpenCLIP ViT-B/32 (~600 MB) are far lighter and
       cleaner to bake into an air-gapped image.

## Risks / Trade-offs

- BGE-M3 is large (~570 MB). Mitigation: default to BGE-base-en-v1.5;
  document the M3 path for users who want it.
- Reranker latency adds ~100-200 ms per query on CPU. Acceptable for
  v0.1; budgeted in the agent end-to-end SLO.
- Two image embedding models (BGE-M3 + OpenCLIP) double the warm-up
  cost on first run. Mitigation: cache locally and pre-bake into the
  ingestion image; combined memory footprint (~1.2 GB) is still well
  under the BLIP-2 alternative.
- Querying two collections per multimodal query roughly doubles
  retrieval latency on the multimodal path. Acceptable: this only fires
  when the query intent is multimodal (router decides); text-only
  queries are unchanged.
- SPEC §11: scope creep risk. We resist adding query rewriting, HyDE, or
  custom rerankers at v0.1.
