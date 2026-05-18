"""Pure render/splice logic for the nightly benchmark refresh."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eval.render_benchmarks import END, START, render, splice

_FORECAST = {
    "skipped": ["patchtst", "ensemble"],
    "results": [
        {
            "tag": "XMEAS_1",
            "model": "naive",
            "n_test": 418,
            "mae": 0.458,
            "rmse": 0.508,
            "smape": 12.3,
        },
        {
            "tag": "XMEAS_1",
            "model": "lgbm",
            "n_test": 418,
            "mae": 0.134,
            "rmse": 0.168,
            "smape": 4.1,
        },
    ],
}
_ANOMALY = [
    {
        "fault_id": 1,
        "fault_profile": "step",
        "threshold": 0.918,
        "precision": 1.0,
        "recall": 0.999,
        "f1": 0.999,
        "n_alert_windows": 719,
        "n_truth_windows": 720,
    }
]


def test_render_contains_both_tables_and_skipped_note() -> None:
    out = render(_FORECAST, _ANOMALY, now=datetime(2026, 5, 18, 3, 17, tzinfo=UTC))
    assert "2026-05-18 03:17 UTC" in out
    assert "### Forecast" in out and "### Anomaly detection" in out
    assert "XMEAS_1 | lgbm" in out
    assert "| 1 | step |" in out
    assert "Skipped models: patchtst, ensemble" in out


def test_render_handles_missing_inputs() -> None:
    out = render(None, None)
    assert "_No forecast results._" in out
    assert "_No anomaly results._" in out


def test_splice_replaces_only_between_markers_idempotently() -> None:
    doc = f"# Benchmarks\n\nintro\n\n{START}\nOLD\n{END}\n\n## Tail\nkeep me\n"
    once = splice(doc, "NEW BLOCK")
    assert "OLD" not in once
    assert "NEW BLOCK" in once
    assert once.startswith("# Benchmarks")
    assert "## Tail\nkeep me" in once
    assert once.count(START) == 1 and once.count(END) == 1
    # Re-splicing with the same block is a no-op (stable nightly diffs).
    assert splice(once, "NEW BLOCK") == once


def test_splice_requires_markers() -> None:
    with pytest.raises(ValueError, match="missing"):
        splice("# Benchmarks\nno markers here\n", "X")
