"""Shared synthetic data for anomaly-detection tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def baseline_panel() -> pd.DataFrame:
    """1-Hz, 30-minute panel of 5 weakly-correlated tags. No faults."""
    rng = np.random.default_rng(42)
    n = 30 * 60
    idx = pd.date_range(start="2026-01-01", periods=n, freq="1s", tz="UTC")
    tags = [f"X_{i}" for i in range(5)]
    cov = np.eye(5) * 0.5 + 0.1
    samples = rng.multivariate_normal(mean=np.zeros(5), cov=cov, size=n)
    return pd.DataFrame(samples + np.array([10, 20, 30, 40, 50]), index=idx, columns=tags)


@pytest.fixture
def faulty_panel(baseline_panel: pd.DataFrame) -> pd.DataFrame:
    """Same shape, with a step shift on tag X_0 in the latter half."""
    out = baseline_panel.copy()
    half = len(out) // 2
    out.iloc[half:, 0] = out.iloc[half:, 0] + 5.0
    return out
