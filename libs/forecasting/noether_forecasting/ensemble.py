"""Two-model ensemble: convex combination of LightGBM + PatchTST point forecasts.

Weights are fitted on the validation fold by minimising MSE under the
sum-to-one + non-negativity constraint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.patchtst import PatchTSTForecaster
from noether_forecasting.protocol import ForecastResult


@dataclass
class EnsembleForecaster:
    tag: str
    horizon_min: int = 30
    model_version: str = "ensemble-v0"
    model_kind: str = "ensemble"

    lgbm: LightGBMForecaster | None = None
    patchtst: PatchTSTForecaster | None = None
    weight_lgbm: float = 0.5
    weight_patchtst: float = 0.5
    _residual_std: float = 0.0
    _val_mse: float = field(default=float("nan"))

    def fit_weights(self, y_val: np.ndarray, y_lgbm: np.ndarray, y_patchtst: np.ndarray) -> None:
        """Fit convex weights on validation predictions."""
        # Drop rows where either prediction is NaN (PatchTST cold-start edge).
        mask = np.isfinite(y_val) & np.isfinite(y_lgbm) & np.isfinite(y_patchtst)
        y_val = y_val[mask]
        y_lgbm = y_lgbm[mask]
        y_patchtst = y_patchtst[mask]
        if len(y_val) < 2:
            self.weight_lgbm = 1.0
            self.weight_patchtst = 0.0
            self._residual_std = 0.0
            self._val_mse = float("nan")
            return

        def loss(w_lgbm: float) -> float:
            w_lgbm = float(np.clip(w_lgbm, 0.0, 1.0))
            yhat = w_lgbm * y_lgbm + (1.0 - w_lgbm) * y_patchtst
            return float(np.mean((yhat - y_val) ** 2))

        result = minimize(
            lambda x: loss(x[0]),
            x0=np.array([0.5]),
            bounds=[(0.0, 1.0)],
            method="L-BFGS-B",
        )
        w = float(np.clip(result.x[0], 0.0, 1.0))
        self.weight_lgbm = w
        self.weight_patchtst = 1.0 - w
        ensemble_val = w * y_lgbm + (1.0 - w) * y_patchtst
        self._residual_std = float(np.std(y_val - ensemble_val, ddof=1))
        self._val_mse = float(np.mean((y_val - ensemble_val) ** 2))

    def predict(self, X: pd.DataFrame, series: pd.Series) -> ForecastResult:
        if self.lgbm is None or self.patchtst is None:
            raise RuntimeError("ensemble missing a member; was it loaded with both artefacts?")
        lgbm_res = self.lgbm.predict(X)
        patchtst_res = self.patchtst.predict(series)
        point = self.weight_lgbm * lgbm_res.point + self.weight_patchtst * patchtst_res.point
        half = (
            1.96 * self._residual_std
            if self._residual_std > 0
            else max(
                abs(lgbm_res.upper - lgbm_res.point),
                abs(patchtst_res.upper - patchtst_res.point),
            )
        )
        return ForecastResult(
            tag=self.tag,
            horizon_min=self.horizon_min,
            point=point,
            lower=point - half,
            upper=point + half,
            model_version=self.model_version,
            model_kind="ensemble",
        )

    def predict_batch(
        self,
        X: pd.DataFrame,
        series: pd.Series,
        eval_index: pd.DatetimeIndex,
    ) -> np.ndarray:
        if self.lgbm is None or self.patchtst is None:
            raise RuntimeError("ensemble missing a member; was it loaded with both artefacts?")
        lgbm_preds = self.lgbm.predict_batch(X.loc[eval_index])
        patchtst_preds = self.patchtst.predict_batch(series, eval_index)
        return self.weight_lgbm * lgbm_preds + self.weight_patchtst * patchtst_preds

    def save(self, path: Path) -> None:
        if self.lgbm is None or self.patchtst is None:
            raise RuntimeError("ensemble missing a member")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Sibling artefacts: lgbm/patchtst saved alongside the ensemble blob.
        # Names follow the registry's extension dispatch.
        member_dir = path.parent
        stem = path.stem  # e.g. xmeas_1
        lgbm_path = member_dir / f"{stem}.lgbm"
        patchtst_path = member_dir / f"{stem}.patchtst"
        self.lgbm.save(lgbm_path)
        self.patchtst.save(patchtst_path)
        joblib.dump(
            {
                "tag": self.tag,
                "horizon_min": self.horizon_min,
                "model_version": self.model_version,
                "weight_lgbm": self.weight_lgbm,
                "weight_patchtst": self.weight_patchtst,
                "residual_std": self._residual_std,
                "val_mse": self._val_mse,
                "lgbm_path": str(lgbm_path.name),
                "patchtst_path": str(patchtst_path.name),
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> EnsembleForecaster:
        bundle = joblib.load(path)
        member_dir = path.parent
        f = cls(
            tag=bundle["tag"],
            horizon_min=bundle["horizon_min"],
            model_version=bundle["model_version"],
            weight_lgbm=bundle["weight_lgbm"],
            weight_patchtst=bundle["weight_patchtst"],
        )
        f._residual_std = bundle["residual_std"]
        f._val_mse = bundle.get("val_mse", float("nan"))
        f.lgbm = LightGBMForecaster.load(member_dir / bundle["lgbm_path"])
        f.patchtst = PatchTSTForecaster.load(member_dir / bundle["patchtst_path"])
        return f
