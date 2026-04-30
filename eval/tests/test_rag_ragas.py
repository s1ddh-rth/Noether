"""Tests for the RAG retrieval-only eval harness.

Stays off docker and off real models — uses Qdrant in-memory + the stub
embedder shipped in `libs/rag` test helpers.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from noether_rag.index import Bm25Index, QdrantIndex
from noether_rag.ingest import ingest_dir
from noether_rag.tests_helpers import StubTextEmbedder
from qdrant_client import QdrantClient

from eval.rag_ragas import (
    EvalQuestion,
    QuestionResult,
    evaluate,
    load_questions,
    render_benchmarks_row,
    summarise,
)


def test_load_questions_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "qs.jsonl"
    p.write_text(
        '{"question_id": "q1", "question": "What is X?", '
        '"expected_doc_token": "X", "notes": "lookup"}\n'
        '{"question_id": "q2", "question": "How does Y work?", '
        '"expected_doc_token": "Y"}\n'
    )
    qs = load_questions(p)
    assert len(qs) == 2
    assert qs[0] == EvalQuestion(
        question_id="q1",
        question="What is X?",
        expected_doc_token="X",
        notes="lookup",
    )
    assert qs[1].notes == ""


def test_evaluate_records_hit_when_token_in_retrieved_text(
    sample_pdf_path: Path, tmp_path: Path
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(sample_pdf_path, src / "doc.pdf")

    embedder = StubTextEmbedder(dim=8)
    qi = QdrantIndex(client=QdrantClient(":memory:"), collection="eval_test")
    bm = Bm25Index()
    ingest_dir(
        src=src,
        qdrant_index=qi,
        bm25_index=bm,
        embedder=embedder,
        data_dir=tmp_path / "rag-index",
    )

    qs = [
        EvalQuestion("q1", "FT-101 status?", "FT-101"),
        EvalQuestion("q2", "Pumpkin pie?", "Pumpkin"),  # not in fixture
    ]
    results = evaluate(qs, embedder=embedder, qdrant_index=qi, bm25_index=bm)
    by_id = {r.question_id: r for r in results}
    assert by_id["q1"].hit is True
    assert by_id["q2"].hit is False
    assert by_id["q1"].n_retrieved >= 1
    assert by_id["q1"].latency_ms >= 0


def test_summarise_aggregates_hit_rate() -> None:
    results = [
        QuestionResult("q1", "?", "X", hit=True, n_retrieved=5, latency_ms=10.0, top_chunks=[]),
        QuestionResult("q2", "?", "Y", hit=False, n_retrieved=5, latency_ms=20.0, top_chunks=[]),
        QuestionResult("q3", "?", "Z", hit=True, n_retrieved=5, latency_ms=30.0, top_chunks=[]),
    ]
    s = summarise(results)
    assert s["n_questions"] == 3
    assert s["n_hit"] == 2
    assert s["hit_rate"] == 0.6667
    assert s["avg_latency_ms"] == 20.0


def test_summarise_handles_empty_input() -> None:
    s = summarise([])
    assert s == {
        "n_questions": 0,
        "n_hit": 0,
        "hit_rate": 0.0,
        "avg_latency_ms": 0.0,
        "results": [],
    }


def test_render_benchmarks_row_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "benchmarks.md"
    summary = {
        "n_questions": 3,
        "n_hit": 2,
        "hit_rate": 0.6667,
        "avg_latency_ms": 12.3,
        "results": [],
    }
    render_benchmarks_row(summary, target)
    text = target.read_text()
    assert "RAG retrieval" in text
    assert "0.6667" in text
    assert "12.3" in text


def test_render_benchmarks_row_replaces_existing_section(tmp_path: Path) -> None:
    target = tmp_path / "benchmarks.md"
    target.write_text(
        "# Benchmarks\n\n"
        "## RAG retrieval (eval/rag_ragas.py)\n\nold content\n"
        "## Other section\n\nuntouched\n"
    )
    summary = {
        "n_questions": 5,
        "n_hit": 4,
        "hit_rate": 0.8,
        "avg_latency_ms": 7.5,
        "results": [],
    }
    render_benchmarks_row(summary, target)
    text = target.read_text()
    assert "old content" not in text
    assert "0.8" in text
    assert "## Other section" in text  # untouched section preserved
    assert "untouched" in text


def test_load_seed_questions_file_present() -> None:
    """The committed seed file must round-trip cleanly."""
    qs = load_questions(Path("eval/data/rag_eval_questions.jsonl"))
    assert len(qs) >= 1
    assert all(q.expected_doc_token for q in qs)
