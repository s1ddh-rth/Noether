from __future__ import annotations

import pytest
from noether_rag.cli import _build_parser


def test_parser_requires_subcommand() -> None:
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_ingest_subcommand_parses_required_args() -> None:
    from pathlib import Path

    p = _build_parser()
    ns = p.parse_args(["ingest", "--src", "/tmp/src", "--collection", "noether_text"])
    assert ns.command == "ingest"
    assert ns.src == Path("/tmp/src")
    assert ns.collection == "noether_text"
    assert ns.reindex is False


def test_reindex_flag_propagates() -> None:
    p = _build_parser()
    ns = p.parse_args(["ingest", "--src", "/tmp/s", "--collection", "c", "--reindex"])
    assert ns.reindex is True


def test_data_dir_and_qdrant_url_overrides() -> None:
    from pathlib import Path

    p = _build_parser()
    ns = p.parse_args(
        [
            "ingest",
            "--src",
            "/tmp/s",
            "--collection",
            "c",
            "--data-dir",
            "/var/rag",
            "--qdrant-url",
            "http://qdrant:6333",
        ]
    )
    assert ns.data_dir == Path("/var/rag")
    assert ns.qdrant_url == "http://qdrant:6333"
