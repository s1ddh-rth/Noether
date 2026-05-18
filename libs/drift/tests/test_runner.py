"""window_bounds / extract_summary (pure) + the insufficient-data path
of compute_drift (no DB, no Evidently)."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from noether_drift import DriftConfig, compute_drift, extract_summary, window_bounds
from noether_drift.config import DriftSettings
from noether_drift.runner import STATUS_INSUFFICIENT, STATUS_OK
from noether_storage.config import StorageSettings


def test_window_bounds_are_contiguous_half_open() -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    cfg = DriftConfig(reference_window_hours=24, current_window_hours=1, tags=["A"])
    ref_start, ref_end, cur_start, cur_end = window_bounds(now, cfg)
    assert cur_end == now
    # current is the most recent hour; reference is the 24h before it.
    assert (cur_end - cur_start).total_seconds() == 3600
    assert ref_end == cur_start  # contiguous, no gap/overlap
    assert (ref_end - ref_start).total_seconds() == 24 * 3600


def _evidently_like(n_cols: int, n_drifted: int, share: float, drift: bool) -> dict:
    # Mirrors the relevant slice of Evidently's DataDriftPreset .as_dict().
    return {
        "metrics": [
            {"metric": "DataDriftTable", "result": {"unrelated": 1}},
            {
                "metric": "DatasetDriftMetric",
                "result": {
                    "number_of_columns": n_cols,
                    "number_of_drifted_columns": n_drifted,
                    "share_of_drifted_columns": share,
                    "dataset_drift": drift,
                },
            },
        ]
    }


def test_extract_summary_reads_dataset_metric() -> None:
    nf, nd, share, drift = extract_summary(_evidently_like(10, 4, 0.4, False), 0.5)
    assert (nf, nd, share, drift) == (10, 4, 0.4, False)


def test_extract_summary_falls_back_to_threshold_when_verdict_absent() -> None:
    d = {
        "metrics": [
            {
                "result": {
                    "number_of_columns": 4,
                    "number_of_drifted_columns": 3,
                    "share_of_drifted_columns": 0.75,
                }
            }
        ]
    }
    nf, nd, share, drift = extract_summary(d, threshold=0.5)
    assert (nf, nd, share) == (4, 3, 0.75)
    assert drift is True  # 0.75 > 0.5


def test_extract_summary_raises_when_metric_missing() -> None:
    with pytest.raises(ValueError, match="no dataset-drift metric"):
        extract_summary({"metrics": [{"result": {"x": 1}}]}, 0.5)


async def test_compute_drift_insufficient_data(monkeypatch, tmp_path) -> None:
    """Few rows → recorded as insufficient_data, no Evidently import,
    no report file written."""

    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text("tags: [A, B]\nmin_rows: 30\n", encoding="utf-8")

    async def fake_pivot(engine, tags, start, end):
        return pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]})  # 2 < min_rows

    class _Engine:
        async def dispose(self) -> None: ...

    persisted: list = []

    async def fake_persist(dsn, summary):
        persisted.append(summary)

    monkeypatch.setattr("noether_drift.runner.pivot", fake_pivot)
    monkeypatch.setattr("noether_drift.runner.create_async_engine", lambda *_a, **_k: _Engine())
    monkeypatch.setattr("noether_drift.runner._persist_row", fake_persist)

    settings = DriftSettings(DRIFT_CONFIG=str(cfg_path), DRIFT_OUTPUT_DIR=str(tmp_path / "out"))
    summary = await compute_drift(
        now=datetime(2026, 5, 18, tzinfo=UTC),
        settings=settings,
        storage=StorageSettings(),
    )

    assert summary.status == STATUS_INSUFFICIENT
    assert summary.status != STATUS_OK
    assert summary.report_path is None
    assert summary.n_drifted == 0
    assert persisted and persisted[0] is summary
    # Nothing should have been written to the (insufficient) output dir.
    assert not (tmp_path / "out").exists()
