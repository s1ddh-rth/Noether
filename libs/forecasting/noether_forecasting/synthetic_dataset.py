"""Generate offline training data from the synthetic TEP generator.

This is what the inference image uses at build time so it ships with a
working baseline forecaster — no MLflow round-trip needed for v0.1.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from noether_ingest import SyntheticTEP, stream_samples


def generate_offline_panel(
    *,
    seed: int = 42,
    duration_hours: int = 24 * 14,
) -> pd.DataFrame:
    """Wide DataFrame: index=ts (1 Hz), columns=tag names.

    14 days of 1 Hz data is ~1.2M rows × 52 cols. That's enough to train a
    robust LightGBM forecaster after resampling to 1-minute means.
    """
    gen = SyntheticTEP(seed=seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[dict] = []
    iterator = stream_samples(gen, start=start, dt=timedelta(seconds=1))
    n = duration_hours * 3600
    for _ in range(n):
        ts, sample = next(iterator)
        rec = {"ts": ts, **sample}
        rows.append(rec)
    df = pd.DataFrame(rows).set_index("ts")
    return df
