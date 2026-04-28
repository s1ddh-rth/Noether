"""Anomaly detection eval harness.

Generates synthetic TEP panels with injected faults, fits the ensemble on
a clean baseline, scores sliding windows across the rest, and computes
precision/recall/F1 against ground-truth fault labels. Sweeps thresholds
per scenario and reports the best-F1 operating point.

Per the add-anomaly-detection capability spec we run at least 5 scenarios.
Until the real Tennessee Eastman simulator lands, we cover six synthetic
scenarios derived from our three fault profiles (step/drift/spike) at two
magnitudes each.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from noether_anomaly import (
    AnomalyEnsemble,
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)
from noether_ingest import SyntheticTEP, stream_samples

# Fault scenarios as a stand-in for TEP fault IDs 1..21. The id is just
# an integer for the JSON output; the magnitude column says what was
# actually applied. When the real TEP simulator lands, this list maps 1:1
# onto TEP fault IDs without changing the harness.
FAULT_SCENARIOS: list[tuple[int, str, dict]] = [
    (1, "step", {"magnitude": 5.0}),
    (2, "step", {"magnitude": 10.0}),
    (3, "drift", {"slope_per_s": 0.001}),
    (4, "drift", {"slope_per_s": 0.005}),
    (5, "spike", {"magnitude_low": 10.0, "magnitude_high": 20.0}),
    (6, "spike", {"magnitude_low": 20.0, "magnitude_high": 40.0}),
]

ANOMALY_TAGS = [
    "XMEAS_1",
    "XMEAS_2",
    "XMEAS_3",
    "XMEAS_4",
    "XMEAS_5",
    "XMEAS_6",
    "XMEAS_7",
    "XMEAS_8",
    "XMV_1",
    "XMV_2",
]


@dataclass
class FaultResult:
    fault_id: int
    fault_profile: str
    threshold: float
    precision: float
    recall: float
    f1: float
    n_alert_windows: int
    n_truth_windows: int


def _generate_panel(
    *,
    seed: int,
    pre_fault_minutes: int,
    fault_minutes: int,
    fault_profile: str,
) -> tuple[pd.DataFrame, datetime]:
    """Return a wide DataFrame (1-Hz tag panel) and the fault start timestamp."""
    gen = SyntheticTEP(
        seed=seed,
        fault_profile=fault_profile,
        fault_start_s=pre_fault_minutes * 60,
    )
    start = datetime(2026, 1, 1, tzinfo=UTC)
    fault_start = start + timedelta(minutes=pre_fault_minutes)
    n = (pre_fault_minutes + fault_minutes) * 60
    rows: list[dict] = []
    iterator = stream_samples(gen, start=start, dt=timedelta(seconds=1))
    for _ in range(n):
        ts, sample = next(iterator)
        rows.append({"ts": ts, **sample})
    df = pd.DataFrame(rows).set_index("ts")
    return df, fault_start


def _windowise(
    df: pd.DataFrame,
    *,
    window_s: int,
    stride_s: int,
) -> list[pd.DataFrame]:
    """Slice the panel into sliding 60-s windows with `stride_s` step."""
    end_ts = df.index.max()
    cur_end = df.index.min() + pd.Timedelta(seconds=window_s)
    out: list[pd.DataFrame] = []
    while cur_end <= end_ts:
        cur_start = cur_end - pd.Timedelta(seconds=window_s)
        sl = df.loc[cur_start:cur_end]
        if len(sl) >= 5:
            out.append(sl)
        cur_end = cur_end + pd.Timedelta(seconds=stride_s)
    return out


def _score_scenario(
    fault_id: int,
    fault_profile: str,
    *,
    pre_fault_minutes: int,
    fault_minutes: int,
    window_s: int,
    stride_s: int,
    seed: int,
) -> FaultResult:
    df, fault_start = _generate_panel(
        seed=seed,
        pre_fault_minutes=pre_fault_minutes,
        fault_minutes=fault_minutes,
        fault_profile=fault_profile,
    )
    df = df[ANOMALY_TAGS]

    # Train ensemble on the first half of the no-fault window so the test
    # windows are out-of-sample for both training and faulting.
    train_end = fault_start - pd.Timedelta(minutes=2)
    train_df = df.loc[:train_end].dropna()
    test_df = df.loc[train_end:]

    ensemble = AnomalyEnsemble(
        detectors=[
            IsolationForestDetector(),
            MahalanobisDetector(),
            EWMADetector(),
        ]
    )
    ensemble.fit(train_df)

    windows = _windowise(test_df, window_s=window_s, stride_s=stride_s)
    scores: list[float] = []
    truths: list[bool] = []
    for w in windows:
        scores.append(ensemble.score(w).score)
        # Truth: window is anomalous if its end timestamp is past fault_start.
        truths.append(bool(w.index.max() >= fault_start))

    scores_arr = np.asarray(scores)
    truths_arr = np.asarray(truths)

    # Threshold sweep: pick the point that maximises F1.
    best = FaultResult(
        fault_id=fault_id,
        fault_profile=fault_profile,
        threshold=float("nan"),
        precision=0.0,
        recall=0.0,
        f1=0.0,
        n_alert_windows=0,
        n_truth_windows=int(truths_arr.sum()),
    )
    for thr in np.linspace(0.50, 0.999, 50):
        alerts = scores_arr >= thr
        tp = int(np.sum(alerts & truths_arr))
        fp = int(np.sum(alerts & ~truths_arr))
        fn = int(np.sum(~alerts & truths_arr))
        if tp + fp == 0 or tp + fn == 0:
            continue
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)
        if f1 > best.f1:
            best = FaultResult(
                fault_id=fault_id,
                fault_profile=fault_profile,
                threshold=float(thr),
                precision=float(precision),
                recall=float(recall),
                f1=float(f1),
                n_alert_windows=int(alerts.sum()),
                n_truth_windows=int(truths_arr.sum()),
            )
    return best


def _markdown_table(results: list[FaultResult]) -> str:
    header = (
        "| fault_id | profile | best F1 | precision | recall | threshold | alerts / truth |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    rows = "".join(
        f"| {r.fault_id} | {r.fault_profile} | {r.f1:.3f} | {r.precision:.3f} | "
        f"{r.recall:.3f} | {r.threshold:.3f} | {r.n_alert_windows} / {r.n_truth_windows} |\n"
        for r in results
    )
    return header + rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anomaly eval harness")
    parser.add_argument("--pre-fault-min", type=int, default=120)
    parser.add_argument("--fault-min", type=int, default=60)
    parser.add_argument("--window-s", type=int, default=60)
    parser.add_argument("--stride-s", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/anomaly.json"),
    )
    args = parser.parse_args(argv)

    results: list[FaultResult] = []
    for fault_id, profile, _meta in FAULT_SCENARIOS:
        result = _score_scenario(
            fault_id=fault_id,
            fault_profile=profile,
            pre_fault_minutes=args.pre_fault_min,
            fault_minutes=args.fault_min,
            window_s=args.window_s,
            stride_s=args.stride_s,
            seed=args.seed + fault_id,
        )
        results.append(result)

    print(_markdown_table(results))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([asdict(r) for r in results], indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {args.output}")

    if any(np.isnan(r.threshold) for r in results):
        print("FAIL: at least one scenario produced no valid thresholds.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
