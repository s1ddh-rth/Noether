from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from noether_forecasting.features import FeatureSpec, build_features, train_val_test_split
from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.protocol import Forecaster


def _series(hours: int = 12) -> pd.Series:
    n = hours * 3600
    idx = pd.date_range(start=datetime(2026, 1, 1, tzinfo=UTC), periods=n, freq="1s")
    rng = np.random.default_rng(7)
    v = 100 + 5 * np.sin(2 * np.pi * np.arange(n) / (24 * 3600)) + 0.5 * rng.standard_normal(n)
    return pd.Series(v, index=idx)


@pytest.fixture
def trained_lgbm() -> LightGBMForecaster:
    X, y = build_features(_series(), FeatureSpec(horizon_min=10))
    X_tr, X_va, _X_te, y_tr, y_va, _y_te = train_val_test_split(X, y)
    model = LightGBMForecaster(tag="XMEAS_1", horizon_min=10)
    model.fit(X_tr, y_tr, X_va, y_va)
    return model


def test_lgbm_round_trip_save_load(tmp_path: Path, trained_lgbm: LightGBMForecaster) -> None:
    path = tmp_path / "xmeas_1.lgbm"
    trained_lgbm.save(path)
    assert path.exists()
    restored = LightGBMForecaster.load(path)
    assert restored.tag == trained_lgbm.tag
    assert restored.horizon_min == trained_lgbm.horizon_min
    assert restored.model_version == trained_lgbm.model_version


def test_lgbm_predict_returns_envelope(trained_lgbm: LightGBMForecaster) -> None:
    X, _y = build_features(_series(hours=4), FeatureSpec(horizon_min=10))
    result = trained_lgbm.predict(X)
    assert result.tag == "XMEAS_1"
    assert result.horizon_min == 10
    assert result.lower <= result.point <= result.upper
    assert result.model_kind == "lgbm"


def test_lgbm_predict_batch_aligned_with_predict(trained_lgbm: LightGBMForecaster) -> None:
    X, _y = build_features(_series(hours=4), FeatureSpec(horizon_min=10))
    one = trained_lgbm.predict(X)
    batch = trained_lgbm.predict_batch(X)
    np.testing.assert_allclose(batch[-1], one.point, rtol=1e-9)


def test_lgbm_protocol_conformance(trained_lgbm: LightGBMForecaster) -> None:
    assert isinstance(trained_lgbm, Forecaster)
    assert trained_lgbm.model_kind == "lgbm"
    assert callable(trained_lgbm.save)
    assert callable(LightGBMForecaster.load)


def test_lgbm_predict_unfitted_raises() -> None:
    model = LightGBMForecaster(tag="XMEAS_1")
    with pytest.raises(RuntimeError):
        model.predict(pd.DataFrame({"a": [1.0]}))
