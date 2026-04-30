"""Idempotent corpus ingestion.

Pipeline per file:
    1. SHA-256 of file bytes -> doc_id.
    2. `extract_text` -> list[PageText].
    3. `chunk_text` per page -> list[str] -> RagChunk(...).
    4. Embedder.encode -> dense vectors.
    5. QdrantIndex.upsert (idempotent via point_uuid).
    6. After all files: refit BM25 over the full corpus, save pickle.

Idempotency: re-running the CLI on an unchanged source directory does no
embedding work — we read the existing BM25 pickle (if any), inspect its
known doc_ids, and skip any files whose SHA-256 already appears.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from noether_rag.chunker import chunk_text
from noether_rag.embed import Embedder, ImageEmbedder
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.models import RagChunk, SourceType
from noether_rag.parsing import extract_page_images, extract_text


@dataclass(frozen=True, slots=True)
class IngestStats:
    docs_processed: int
    docs_skipped: int
    chunks_indexed: int


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(64 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _file_to_chunks(path: Path, doc_id: str) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    chunk_idx = 0
    for page in extract_text(path):
        for text in chunk_text(page.text):
            chunks.append(
                RagChunk(
                    doc_id=doc_id,
                    chunk_idx=chunk_idx,
                    source_type=SourceType.PDF_TEXT,
                    text=text,
                    metadata={
                        "filename": path.name,
                        "page": page.page_number,
                    },
                )
            )
            chunk_idx += 1
    return chunks


def ingest_dir(
    *,
    src: Path,
    qdrant_index: QdrantIndex,
    bm25_index: Bm25Index,
    embedder: Embedder,
    data_dir: Path,
    reindex: bool = False,
    pattern: str = "*.pdf",
) -> IngestStats:
    """Ingest every `pattern`-matching file under `src` into the indexes."""
    src = Path(src)
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    pickle_path = data_dir / f"{qdrant_index.collection}_bm25.pkl"

    # Determine known doc_ids — either freshly empty or from the existing BM25.
    known_doc_ids: set[str] = set()
    existing_chunks: list[RagChunk] = []
    if not reindex and pickle_path.exists():
        prior = Bm25Index.load(pickle_path)
        existing_chunks = list(prior._chunks)
        known_doc_ids = {c.doc_id for c in existing_chunks}

    new_chunks: list[RagChunk] = []
    docs_processed = 0
    docs_skipped = 0
    seen_doc_ids: set[str] = set(known_doc_ids)

    for path in sorted(src.glob(pattern)):
        doc_id = _file_sha256(path)
        if doc_id in seen_doc_ids:
            docs_skipped += 1
            continue
        seen_doc_ids.add(doc_id)
        new_chunks.extend(_file_to_chunks(path, doc_id))
        docs_processed += 1

    if new_chunks:
        vectors = embedder.encode([c.text for c in new_chunks])
        qdrant_index.ensure_collection(dim=embedder.dim)
        qdrant_index.upsert(new_chunks, vectors)

    all_chunks = (existing_chunks if not reindex else []) + new_chunks
    bm25_index.fit(all_chunks)
    bm25_index.save(pickle_path)

    return IngestStats(
        docs_processed=docs_processed,
        docs_skipped=docs_skipped,
        chunks_indexed=len(all_chunks),
    )


def _file_to_image_chunks(path: Path, doc_id: str, dpi: int) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    for chunk_idx, page in enumerate(extract_page_images(path, dpi=dpi)):
        chunks.append(
            RagChunk(
                doc_id=doc_id,
                chunk_idx=chunk_idx,
                source_type=SourceType.PID_IMAGE,
                # No body text for image chunks; the diagram is the payload.
                # The reranker (text-side) won't be effective on these alone,
                # which is why retrieve() should fuse text + image collections
                # via RRF before reranking.
                text="",
                metadata={
                    "filename": path.name,
                    "page": page.page_number,
                    "dpi": dpi,
                },
            )
        )
    return chunks


def ingest_dir_multimodal(
    *,
    src: Path,
    qdrant_index: QdrantIndex,
    image_embedder: ImageEmbedder,
    dpi: int = 100,
    pattern: str = "*.pdf",
) -> IngestStats:
    """Ingest each PDF page as a P&ID-style image chunk into a Qdrant collection.

    Mirrors `ingest_dir` for the multimodal path: SHA-256 dedup at the
    document level, point-uuid stable across reruns. No BM25 here — image
    chunks have empty text; sparse retrieval is unhelpful for them, and
    the agent's multimodal route fuses image hits with text hits from the
    text-RAG collection at retrieve time.
    """
    src = Path(src)
    qdrant_index.ensure_collection(dim=image_embedder.dim)

    new_chunks: list[RagChunk] = []
    images_to_embed: list[Image.Image] = []
    docs_processed = 0
    docs_skipped = 0
    # Seed seen_doc_ids from any prior run by scrolling the collection's
    # payloads. Cheap for v0.1 corpus sizes; if this becomes hot, swap to
    # a small on-disk manifest like the text path's BM25 pickle.
    seen_doc_ids: set[str] = set(qdrant_index.known_doc_ids())

    for path in sorted(src.glob(pattern)):
        doc_id = _file_sha256(path)
        if doc_id in seen_doc_ids:
            docs_skipped += 1
            continue
        seen_doc_ids.add(doc_id)
        page_images = extract_page_images(path, dpi=dpi)
        for chunk in _file_to_image_chunks(path, doc_id, dpi):
            new_chunks.append(chunk)
        images_to_embed.extend(p.image for p in page_images)
        docs_processed += 1

    if new_chunks:
        vectors = image_embedder.encode_image(images_to_embed)
        qdrant_index.upsert(new_chunks, vectors)

    return IngestStats(
        docs_processed=docs_processed,
        docs_skipped=docs_skipped,
        chunks_indexed=qdrant_index.count(),
    )
