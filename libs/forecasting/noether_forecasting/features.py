"""Feature engineering for tag time series.

Pipeline:
    1) Resample 1 Hz raw samples to 1-minute means (forward-fill gaps).
    2) Build lag/rolling features for one target tag.
    3) Time-based train/val/test split.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def resample_1min(series: pd.Series) -> pd.Series:
    """1 Hz → 1-minute mean. Forward-fill gaps up to 5 minutes; drop longer gaps.

    Input: a tz-aware DatetimeIndex pandas Series of floats.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("series must have a DatetimeIndex")
    resampled = series.resample("1min").mean()
    return resampled.ffill(limit=5)


@dataclass(frozen=True)
class FeatureSpec:
    lags: tuple[int, ...] = (1, 2, 3, 5, 10, 30, 60)
    rolling_windows: tuple[int, ...] = (5, 15, 60)
    horizon_min: int = 30


def build_features(
    series: pd.Series,
    spec: FeatureSpec | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return X, y where y is the value `horizon_min` minutes ahead.

    X columns: lag_<k>, rmean_<w>, rstd_<w>, hour_sin, hour_cos.
    """
    spec = spec or FeatureSpec()
    s = resample_1min(series).dropna()
    df = pd.DataFrame(index=s.index)
    df["value"] = s

    for k in spec.lags:
        df[f"lag_{k}"] = s.shift(k)
    for w in spec.rolling_windows:
        df[f"rmean_{w}"] = s.shift(1).rolling(w).mean()
        df[f"rstd_{w}"] = s.shift(1).rolling(w).std()

    hour = s.index.hour + s.index.minute / 60.0
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    df["target"] = s.shift(-spec.horizon_min)
    df = df.dropna()

    feature_cols = [c for c in df.columns if c not in {"value", "target"}]
    return df[feature_cols], df["target"]


def train_val_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Strict time-based split — no shuffling, no leakage."""
    n = len(X)
    n_test = int(n * test_frac)
    n_val = int(n * val_frac)
    n_train = n - n_val - n_test
    if min(n_train, n_val, n_test) < 1:
        raise ValueError(f"not enough rows to split: have {n}")
    return (
        X.iloc[:n_train],
        X.iloc[n_train : n_train + n_val],
        X.iloc[n_train + n_val :],
        y.iloc[:n_train],
        y.iloc[n_train : n_train + n_val],
        y.iloc[n_train + n_val :],
    )
