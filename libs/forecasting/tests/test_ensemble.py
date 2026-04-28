"""Numeric tests for EnsembleForecaster.fit_weights — no torch required."""

import numpy as np
import pytest
from noether_forecasting.ensemble import EnsembleForecaster


def _ensemble() -> EnsembleForecaster:
    return EnsembleForecaster(tag="XMEAS_1", horizon_min=30)


def test_weights_sum_to_one() -> None:
    rng = np.random.default_rng(0)
    y = rng.standard_normal(200)
    y_lgbm = y + rng.standard_normal(200) * 0.1
    y_patchtst = y + rng.standard_normal(200) * 0.5
    e = _ensemble()
    e.fit_weights(y, y_lgbm, y_patchtst)
    assert pytest.approx(e.weight_lgbm + e.weight_patchtst, abs=1e-9) == 1.0
    assert 0.0 <= e.weight_lgbm <= 1.0
    assert 0.0 <= e.weight_patchtst <= 1.0


def test_weights_favor_better_member() -> None:
    """When LGBM is much better than PatchTST, weight_lgbm should dominate."""
    rng = np.random.default_rng(1)
    y = rng.standard_normal(500)
    y_lgbm = y + rng.standard_normal(500) * 0.05  # tight
    y_patchtst = y + rng.standard_normal(500) * 1.0  # noisy
    e = _ensemble()
    e.fit_weights(y, y_lgbm, y_patchtst)
    assert e.weight_lgbm > 0.7


def test_handles_nan_predictions() -> None:
    """PatchTST cold-start can return NaN — fit_weights must drop, not crash."""
    rng = np.random.default_rng(2)
    y = rng.standard_normal(100)
    y_lgbm = y + rng.standard_normal(100) * 0.1
    y_patchtst = y + rng.standard_normal(100) * 0.1
    y_patchtst[:30] = np.nan  # PatchTST warmup window
    e = _ensemble()
    e.fit_weights(y, y_lgbm, y_patchtst)
    assert np.isfinite(e.weight_lgbm)
    assert np.isfinite(e.weight_patchtst)
    assert e.weight_lgbm + e.weight_patchtst == pytest.approx(1.0, abs=1e-9)


def test_fallback_when_too_few_aligned() -> None:
    """All NaN PatchTST → fall back to LGBM-only weights."""
    y = np.array([1.0, 2.0])
    y_lgbm = np.array([1.0, 2.0])
    y_patchtst = np.array([np.nan, np.nan])
    e = _ensemble()
    e.fit_weights(y, y_lgbm, y_patchtst)
    assert e.weight_lgbm == 1.0
    assert e.weight_patchtst == 0.0
