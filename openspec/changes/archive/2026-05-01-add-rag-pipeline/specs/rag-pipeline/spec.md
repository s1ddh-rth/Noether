## ADDED Requirements

### Requirement: Corpus ingestion CLI
A CLI SHALL build a Qdrant index from a directory of PDFs and image
documents. It SHALL extract text, chunk it, embed each chunk with the
configured BGE model, store vectors and payload in Qdrant, and produce
a sidecar BM25 corpus file for sparse search.

#### Scenario: Index a small corpus
- **WHEN** `python -m libs.rag.cli ingest --src ./data/rag_corpus
  --collection noether` runs against a 10-document corpus
- **THEN** the CLI exits 0
- **AND** Qdrant collection `noether` contains chunks with payload
  fields `doc_id`, `source_type`, `chunk_idx`, `text`
- **AND** `./data/rag_corpus/_bm25.pkl` exists and loads without error

### Requirement: Hybrid search with RRF and reranking
The retrieval API SHALL accept `(query: str, k: int)` and return the top
`k` reranked chunks. Internally it SHALL fetch top-20 from dense
similarity AND top-20 from BM25, fuse via reciprocal rank fusion (k=60),
then rerank the fused top-20 with BGE-reranker-base, returning the
final top-`k`.

#### Scenario: Hybrid search returns ranked chunks
- **WHEN** `retrieve(query="how does fault 4 affect XMEAS_7", k=5)` is
  called against an indexed corpus
- **THEN** the result is a list of 5 chunks
- **AND** each chunk has fields `text`, `doc_id`, `score`
- **AND** scores are non-increasing

### Requirement: Multimodal P&ID retrieval
P&ID image documents SHALL be embedded directly with BGE-M3 and
OpenCLIP (no captioning step) and indexed in two parallel Qdrant
collections. The `retrieve` call SHALL query both collections, merge
results via reciprocal rank fusion, and return P&IDs that match the
query when it references equipment tags or process units present in
the diagram.

#### Scenario: Retrieve a P&ID by tag
- **WHEN** the corpus contains a P&ID labelled with tag `FT-101` and
  `retrieve(query="show me the P&ID containing FT-101", k=5)` is called
- **THEN** at least one returned chunk has `source_type == "pid_image"`
  and references `FT-101`

#### Scenario: No captioning step
- **WHEN** P&ID ingestion runs against a directory of image documents
- **THEN** ingestion completes without invoking any captioning model
- **AND** both `noether_mm_bge` and `noether_mm_clip` Qdrant collections
  contain points whose payload `source_type == "pid_image"`

### Requirement: RAGAS eval harness
`eval/rag_ragas.py` SHALL compute RAGAS faithfulness, answer relevancy,
and context precision against a question set in
`eval/data/rag_eval_questions.jsonl` and write
`{ "faithfulness": float, "answer_relevancy": float,
"context_precision": float }` to `eval/results/rag.json`.

#### Scenario: Harness produces benchmark file
- **WHEN** `python eval/rag_ragas.py` runs against an indexed corpus
- **THEN** `eval/results/rag.json` exists with all three numeric metrics

### Requirement: Air-gapped operation
All RAG components (ingestion, retrieval, eval) SHALL operate without outbound network calls after a one-time model warm. With `OFFLINE_MODE=1`, ingestion and retrieval SHALL fail fast on any non-allowlisted DNS lookup.

#### Scenario: Air-gapped retrieve
- **WHEN** retrieval is called with `OFFLINE_MODE=1` after a one-time
  model warm
- **THEN** `retrieve(...)` returns successfully
- **AND** no DNS lookups beyond Qdrant occur during the call
