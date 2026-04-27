"""LightGBM tabular forecaster for one tag.

Wraps `lightgbm.LGBMRegressor` with a small Forecaster-Protocol-shaped surface
so the API server can swap models behind the same interface later (PatchTST,
ensemble, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from pydantic import BaseModel

from noether_forecasting.features import FeatureSpec


class ForecastResult(BaseModel):
    tag: str
    horizon_min: int
    point: float
    lower: float
    upper: float
    model_version: str


@dataclass
class LightGBMForecaster:
    tag: str
    horizon_min: int = 30
    model_version: str = "lgbm-v0"

    _booster: lgb.Booster | None = None
    _feature_cols: list[str] | None = None
    _residual_std: float = 0.0

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        *,
        params: dict | None = None,
    ) -> None:
        params = params or {
            "objective": "regression",
            "metric": "rmse",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 50,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
        }
        train_set = lgb.Dataset(X_train, label=y_train)
        val_set = lgb.Dataset(X_val, label=y_val, reference=train_set)

        self._booster = lgb.train(
            params,
            train_set,
            num_boost_round=500,
            valid_sets=[val_set],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)],
        )
        self._feature_cols = list(X_train.columns)
        # Hold-out residual std as a crude prediction-interval width. Replace
        # with quantile regression / conformal in a follow-up change.
        preds = self._booster.predict(X_val, num_iteration=self._booster.best_iteration)
        self._residual_std = float(np.std(np.asarray(y_val) - preds, ddof=1))

    def predict(self, X: pd.DataFrame) -> ForecastResult:
        if self._booster is None or self._feature_cols is None:
            raise RuntimeError("model is not fitted or loaded")
        # Align columns to training order.
        x = X[self._feature_cols].iloc[[-1]]
        point = float(self._booster.predict(x, num_iteration=self._booster.best_iteration)[0])
        # 95% interval using ±1.96 * residual std.
        half = 1.96 * self._residual_std
        return ForecastResult(
            tag=self.tag,
            horizon_min=self.horizon_min,
            point=point,
            lower=point - half,
            upper=point + half,
            model_version=self.model_version,
        )

    def save(self, path: Path) -> None:
        if self._booster is None:
            raise RuntimeError("nothing to save")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "tag": self.tag,
                "horizon_min": self.horizon_min,
                "model_version": self.model_version,
                "booster": self._booster.model_to_string(),
                "feature_cols": self._feature_cols,
                "residual_std": self._residual_std,
                "feature_spec": FeatureSpec().__dict__,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> LightGBMForecaster:
        bundle = joblib.load(path)
        f = cls(
            tag=bundle["tag"],
            horizon_min=bundle["horizon_min"],
            model_version=bundle["model_version"],
        )
        f._booster = lgb.Booster(model_str=bundle["booster"])
        f._feature_cols = bundle["feature_cols"]
        f._residual_std = bundle["residual_std"]
        return f
