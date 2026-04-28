from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from noether_forecasting.features import (
    FeatureSpec,
    build_features,
    resample_1min,
    train_val_test_split,
)


def _hourly_sine(hours: int = 24, freq_s: int = 1) -> pd.Series:
    n = hours * 3600 // freq_s
    idx = pd.date_range(
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        periods=n,
        freq=f"{freq_s}s",
    )
    rng = np.random.default_rng(42)
    values = (
        100.0 + 5.0 * np.sin(2 * np.pi * np.arange(n) / (24 * 3600)) + 0.1 * rng.standard_normal(n)
    )
    return pd.Series(values, index=idx)


def test_resample_1min_collapses_60_to_1() -> None:
    s = _hourly_sine(hours=2)
    out = resample_1min(s)
    assert len(out) == 2 * 60
    assert isinstance(out.index, pd.DatetimeIndex)


def test_resample_1min_rejects_non_datetime_index() -> None:
    s = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(TypeError):
        resample_1min(s)


def test_build_features_columns_match_spec() -> None:
    s = _hourly_sine(hours=6)
    spec = FeatureSpec(horizon_min=10)
    X, y = build_features(s, spec)
    expected_lags = {f"lag_{k}" for k in spec.lags}
    expected_rolling = {f"rmean_{w}" for w in spec.rolling_windows} | {
        f"rstd_{w}" for w in spec.rolling_windows
    }
    assert expected_lags <= set(X.columns)
    assert expected_rolling <= set(X.columns)
    assert {"hour_sin", "hour_cos"} <= set(X.columns)
    assert len(X) == len(y)
    assert len(X) > 0


def test_build_features_target_shifted_by_horizon() -> None:
    s = _hourly_sine(hours=4)
    spec = FeatureSpec(horizon_min=15)
    X, y = build_features(s, spec)
    # The first y value at index t corresponds to s_resampled at t + 15 min.
    s_1min = resample_1min(s).dropna()
    aligned = s_1min.shift(-spec.horizon_min).dropna()
    overlap = y.index.intersection(aligned.index)
    assert len(overlap) > 0
    np.testing.assert_allclose(y.loc[overlap].values, aligned.loc[overlap].values, atol=1e-9)


def test_train_val_test_split_no_overlap() -> None:
    s = _hourly_sine(hours=10)
    X, y = build_features(s, FeatureSpec(horizon_min=10))
    X_tr, X_va, X_te, y_tr, y_va, y_te = train_val_test_split(X, y)
    assert len(X_tr) + len(X_va) + len(X_te) == len(X)
    # Strict time order — train ends before val starts; val ends before test starts.
    assert X_tr.index.max() < X_va.index.min()
    assert X_va.index.max() < X_te.index.min()


def test_train_val_test_split_too_small_raises() -> None:
    idx = pd.date_range(start="2026-01-01", periods=2, freq="min", tz="UTC")
    X = pd.DataFrame({"a": [1.0, 2.0]}, index=idx)
    y = pd.Series([1.0, 2.0], index=idx)
    with pytest.raises(ValueError):
        train_val_test_split(X, y)
