"""Input-drift monitoring for Noether.

A periodic job (compose `cron` profile / Helm CronJob) compares the most
recent ingest window against a preceding reference baseline using
Evidently's DataDriftPreset, writes a full JSON report to a volume, and
records a compact summary row in the `drift_reports` table so Grafana can
chart it via the existing TimescaleDB datasource.
"""

from __future__ import annotations

from noether_drift.config import DriftConfig, DriftSettings, load_drift_config
from noether_drift.runner import DriftSummary, compute_drift, extract_summary, window_bounds

__all__ = [
    "DriftConfig",
    "DriftSettings",
    "DriftSummary",
    "compute_drift",
    "extract_summary",
    "load_drift_config",
    "window_bounds",
]
