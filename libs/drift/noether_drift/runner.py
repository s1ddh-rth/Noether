"""Drift computation: pull two windows from Timescale, run Evidently,
persist a full report + a compact summary row.

The pure helpers (`window_bounds`, `extract_summary`) are unit-tested
without a DB or Evidently; `compute_drift` is the integration entrypoint.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from noether_storage.config import StorageSettings, async_dsn
from noether_storage.query import pivot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from noether_drift.config import DriftConfig, DriftSettings, load_drift_config

log = structlog.get_logger("noether.drift")

# Statuses recorded in drift_reports.status.
STATUS_OK = "ok"
STATUS_INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class DriftSummary:
    """Compact result — mirrors one `drift_reports` row."""

    ts: datetime
    reference_start: datetime
    reference_end: datetime
    current_start: datetime
    current_end: datetime
    n_features: int
    n_drifted: int
    drift_share: float
    dataset_drift: bool
    status: str
    report_path: str | None


def window_bounds(now: datetime, cfg: DriftConfig) -> tuple[datetime, datetime, datetime, datetime]:
    """(ref_start, ref_end, cur_start, cur_end).

    Current = the most recent `current_window_hours`. Reference = the
    `reference_window_hours` immediately preceding it. Half-open
    [start, end) intervals, matching `noether_storage.query`.
    """
    cur_end = now
    cur_start = cur_end - timedelta(hours=cfg.current_window_hours)
    ref_end = cur_start
    ref_start = ref_end - timedelta(hours=cfg.reference_window_hours)
    return ref_start, ref_end, cur_start, cur_end


def extract_summary(report_dict: dict[str, Any], threshold: float) -> tuple[int, int, float, bool]:
    """Pull (n_features, n_drifted, drift_share, dataset_drift) out of an
    Evidently `DataDriftPreset` `.as_dict()`.

    Evidently's dict shape varies across metrics within the preset, so we
    scan every metric's `result` for the dataset-level keys rather than
    assuming a fixed index.
    """
    for metric in report_dict.get("metrics", []):
        result = metric.get("result", {})
        if "number_of_columns" in result and "number_of_drifted_columns" in result:
            n_features = int(result["number_of_columns"])
            n_drifted = int(result["number_of_drifted_columns"])
            share = float(
                result.get(
                    "share_of_drifted_columns",
                    (n_drifted / n_features) if n_features else 0.0,
                )
            )
            # Prefer Evidently's own verdict if present; else apply our
            # configured threshold.
            dataset_drift = bool(result.get("dataset_drift", share > threshold))
            return n_features, n_drifted, share, dataset_drift
    raise ValueError("no dataset-drift metric found in Evidently report")


async def _persist_row(dsn: str, s: DriftSummary) -> None:
    engine = create_async_engine(dsn)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO drift_reports (
                        ts, reference_start, reference_end,
                        current_start, current_end, n_features,
                        n_drifted, drift_share, dataset_drift,
                        status, report_path
                    ) VALUES (
                        :ts, :rs, :re, :cs, :ce, :nf,
                        :nd, :ds, :dd, :st, :rp
                    )
                """),
                {
                    "ts": s.ts,
                    "rs": s.reference_start,
                    "re": s.reference_end,
                    "cs": s.current_start,
                    "ce": s.current_end,
                    "nf": s.n_features,
                    "nd": s.n_drifted,
                    "ds": s.drift_share,
                    "dd": s.dataset_drift,
                    "st": s.status,
                    "rp": s.report_path,
                },
            )
    finally:
        await engine.dispose()


def _write_reports(output_dir: Path, run_ts: datetime, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = run_ts.strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"drift-{stamp}.json"
    blob = json.dumps(payload, default=str, indent=2)
    path.write_text(blob, encoding="utf-8")
    # `latest.json` is a stable filename for ad-hoc inspection.
    (output_dir / "latest.json").write_text(blob, encoding="utf-8")
    return path


async def compute_drift(
    *,
    now: datetime | None = None,
    settings: DriftSettings | None = None,
    storage: StorageSettings | None = None,
) -> DriftSummary:
    """Run one drift evaluation. One-shot — the scheduler is external
    (Helm CronJob / compose `cron` loop)."""
    settings = settings or DriftSettings()
    storage = storage or StorageSettings()
    cfg: DriftConfig = load_drift_config(settings.config_path)
    run_ts = now or datetime.now(UTC)

    ref_start, ref_end, cur_start, cur_end = window_bounds(run_ts, cfg)
    dsn = async_dsn(storage)
    engine = create_async_engine(dsn)
    try:
        ref_df = await pivot(engine, cfg.tags, ref_start, ref_end)
        cur_df = await pivot(engine, cfg.tags, cur_start, cur_end)
    finally:
        await engine.dispose()

    output_dir = Path(settings.output_dir)

    if len(ref_df) < cfg.min_rows or len(cur_df) < cfg.min_rows:
        log.warning(
            "drift.insufficient_data",
            ref_rows=len(ref_df),
            cur_rows=len(cur_df),
            min_rows=cfg.min_rows,
        )
        summary = DriftSummary(
            ts=run_ts,
            reference_start=ref_start,
            reference_end=ref_end,
            current_start=cur_start,
            current_end=cur_end,
            n_features=len(cfg.tags),
            n_drifted=0,
            drift_share=0.0,
            dataset_drift=False,
            status=STATUS_INSUFFICIENT,
            report_path=None,
        )
        await _persist_row(dsn, summary)
        return summary

    # Imported lazily: Evidently is a heavy import and only needed when
    # there is actually data to evaluate.
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_df, current_data=cur_df)
    report_dict = report.as_dict()
    n_features, n_drifted, share, dataset_drift = extract_summary(
        report_dict, cfg.drift_share_threshold
    )

    report_path = _write_reports(
        output_dir,
        run_ts,
        {
            "generated_at": run_ts,
            "windows": {
                "reference": [ref_start, ref_end],
                "current": [cur_start, cur_end],
            },
            "summary": {
                "n_features": n_features,
                "n_drifted": n_drifted,
                "drift_share": share,
                "dataset_drift": dataset_drift,
            },
            "evidently": report_dict,
        },
    )

    summary = DriftSummary(
        ts=run_ts,
        reference_start=ref_start,
        reference_end=ref_end,
        current_start=cur_start,
        current_end=cur_end,
        n_features=n_features,
        n_drifted=n_drifted,
        drift_share=share,
        dataset_drift=dataset_drift,
        status=STATUS_OK,
        report_path=str(report_path),
    )
    await _persist_row(dsn, summary)
    log.info("drift.computed", **{k: v for k, v in asdict(summary).items() if k != "ts"})
    return summary
