"""RAG retrieval-only eval harness.

What this ships now (Phase 2):
    For each question in `eval/data/rag_eval_questions.jsonl`, runs
    `retrieve()` against a configured corpus and records hit-rate against
    a ground-truth lexical token (a unique substring expected to appear
    in *some* retrieved chunk). Writes `eval/results/rag.json` and a
    Markdown row in `docs/benchmarks.md`.

What it does NOT ship yet:
    The proper RAGAS faithfulness / answer_relevancy / context_precision
    metrics from the OpenSpec proposal. Those metrics need an LLM to
    score generated answers, and the LLM provider abstraction lands in
    the next M3 change (`add-agent-system`). At that point this harness
    will gain an `--llm` flag and write the real RAGAS scores; the
    plumbing here (loader, runner, JSON output, benchmarks rendering) is
    designed to plug straight in.

Usage:
    python -m eval.rag_ragas --corpus DIR --collection NAME [--questions FILE]
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from noether_rag.embed import BgeTextEmbedder, Embedder
from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import ingest_dir
from noether_rag.retrieve import retrieve
from qdrant_client import QdrantClient

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS = ROOT / "eval" / "data" / "rag_eval_questions.jsonl"
DEFAULT_RESULTS = ROOT / "eval" / "results" / "rag.json"
DEFAULT_BENCHMARKS = ROOT / "docs" / "benchmarks.md"


@dataclass(frozen=True, slots=True)
class EvalQuestion:
    question_id: str
    question: str
    expected_doc_token: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class QuestionResult:
    question_id: str
    question: str
    expected_doc_token: str
    hit: bool
    n_retrieved: int
    latency_ms: float
    top_chunks: list[str]


def load_questions(path: Path) -> list[EvalQuestion]:
    """Read JSONL question file. One JSON object per line."""
    out: list[EvalQuestion] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append(
                EvalQuestion(
                    question_id=obj["question_id"],
                    question=obj["question"],
                    expected_doc_token=obj["expected_doc_token"],
                    notes=obj.get("notes", ""),
                )
            )
    return out


def evaluate(
    questions: Iterable[EvalQuestion],
    *,
    embedder: Embedder,
    qdrant_index: QdrantIndex,
    bm25_index: Bm25Index,
    top_n: int = 5,
) -> list[QuestionResult]:
    """Run each question through retrieve() and record hit / latency / top chunks."""
    results: list[QuestionResult] = []
    for q in questions:
        t0 = time.perf_counter()
        retrieved = retrieve(
            q.question,
            embedder=embedder,
            qdrant_indexes=[qdrant_index],
            bm25_index=bm25_index,
            reranker=None,
            top_n=top_n,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        hit = any(q.expected_doc_token in r.chunk.text for r in retrieved)
        top_chunks = [r.chunk.text[:200] for r in retrieved]
        results.append(
            QuestionResult(
                question_id=q.question_id,
                question=q.question,
                expected_doc_token=q.expected_doc_token,
                hit=hit,
                n_retrieved=len(retrieved),
                latency_ms=round(latency_ms, 1),
                top_chunks=top_chunks,
            )
        )
    return results


def summarise(results: list[QuestionResult]) -> dict[str, object]:
    n = len(results)
    n_hit = sum(1 for r in results if r.hit)
    avg_latency = round(sum(r.latency_ms for r in results) / n, 1) if n else 0.0
    return {
        "n_questions": n,
        "n_hit": n_hit,
        "hit_rate": round(n_hit / n, 4) if n else 0.0,
        "avg_latency_ms": avg_latency,
        "results": [asdict(r) for r in results],
    }


def render_benchmarks_row(summary: dict[str, object], target: Path) -> None:
    """Append or update the RAG row in docs/benchmarks.md."""
    target.parent.mkdir(parents=True, exist_ok=True)
    header = "## RAG retrieval (eval/rag_ragas.py)"
    table_header = (
        "| Metric | Value |\n"
        "|---|---|\n"
        f"| n_questions | {summary['n_questions']} |\n"
        f"| hit_rate (top-5) | {summary['hit_rate']} |\n"
        f"| avg_latency_ms | {summary['avg_latency_ms']} |\n"
    )
    note = (
        "\n_LLM-dependent RAGAS metrics (faithfulness, answer_relevancy,"
        " context_precision) ship with the agent service in the next M3"
        " change. Until then this harness reports retrieval hit-rate against"
        " ground-truth lexical tokens._\n"
    )
    body = f"\n{header}\n\n{table_header}{note}\n"

    if not target.exists():
        target.write_text("# Benchmarks\n" + body)
        return
    text = target.read_text()
    if header in text:
        # Replace from the header to the end of the section (next ## or EOF).
        idx = text.index(header)
        # Find next "## " heading after our section.
        rest_idx = text.find("\n## ", idx + len(header))
        suffix = text[rest_idx:] if rest_idx != -1 else ""
        text = text[:idx].rstrip() + body.rstrip() + "\n" + suffix
    else:
        text = text.rstrip() + body
    target.write_text(text)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rag_ragas")
    p.add_argument("--corpus", type=Path, required=True, help="Source PDF directory.")
    p.add_argument("--collection", default="rag_eval", help="Qdrant collection name.")
    p.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help="Path to rag_eval_questions.jsonl.",
    )
    p.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
        help="Path to write rag.json results.",
    )
    p.add_argument(
        "--benchmarks",
        type=Path,
        default=DEFAULT_BENCHMARKS,
        help="Markdown file to update with the RAG row.",
    )
    p.add_argument(
        "--in-memory",
        action="store_true",
        help="Use Qdrant in-memory client (default uses RAG_QDRANT_URL).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    questions = load_questions(args.questions)

    embedder = BgeTextEmbedder()
    client = (
        QdrantClient(":memory:") if args.in_memory else QdrantClient(url="http://localhost:6333")
    )
    qi = QdrantIndex(client=client, collection=args.collection)
    qi.ensure_collection(dim=embedder.dim)
    bm = Bm25Index()

    ingest_dir(
        src=args.corpus,
        qdrant_index=qi,
        bm25_index=bm,
        embedder=embedder,
        data_dir=args.results.parent,
    )

    results = evaluate(
        questions,
        embedder=embedder,
        qdrant_index=qi,
        bm25_index=bm,
    )
    summary = summarise(results)

    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(json.dumps(summary, indent=2))
    render_benchmarks_row(summary, args.benchmarks)

    print(
        f"rag_ragas: hit_rate={summary['hit_rate']} "
        f"avg_latency_ms={summary['avg_latency_ms']} "
        f"n={summary['n_questions']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
