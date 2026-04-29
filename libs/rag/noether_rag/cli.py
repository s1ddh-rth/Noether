"""Command-line entrypoint for `noether_rag` ingestion.

    python -m noether_rag.cli ingest --src ./data/rag-corpus \
        --collection noether_text

The CLI delegates to `ingest_dir`, which is exercised under unit tests
with stubbed embedders + in-memory Qdrant. This module is intentionally
thin so almost nothing goes untested.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from qdrant_client import QdrantClient

from noether_rag.embed import BgeTextEmbedder
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import ingest_dir


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="noether_rag")
    sub = p.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest", help="Ingest a directory of PDFs.")
    ing.add_argument("--src", type=Path, required=True, help="Source directory.")
    ing.add_argument("--collection", required=True, help="Qdrant collection name.")
    ing.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.getenv("RAG_DATA_DIR", "./data/rag-index")),
        help="Where to store the BM25 pickle.",
    )
    ing.add_argument(
        "--qdrant-url",
        default=os.getenv("RAG_QDRANT_URL", "http://localhost:6333"),
        help="Qdrant HTTP endpoint.",
    )
    ing.add_argument(
        "--reindex",
        action="store_true",
        help="Drop prior BM25 state and re-ingest everything.",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command != "ingest":  # pragma: no cover — argparse rejects others
        return 2

    qi = QdrantIndex(
        client=QdrantClient(url=args.qdrant_url),
        collection=args.collection,
    )
    embedder = BgeTextEmbedder()
    qi.ensure_collection(dim=embedder.dim)
    bm = Bm25Index()
    stats = ingest_dir(
        src=args.src,
        qdrant_index=qi,
        bm25_index=bm,
        embedder=embedder,
        data_dir=args.data_dir,
        reindex=args.reindex,
    )
    print(
        f"ingest: processed={stats.docs_processed} "
        f"skipped={stats.docs_skipped} chunks_indexed={stats.chunks_indexed}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
