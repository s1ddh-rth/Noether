"""PatchTST forecaster via Nixtla `neuralforecast`.

Operates on a 1-minute resampled univariate series. Wraps NeuralForecast
behind the same metadata/persistence surface as LightGBMForecaster.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from noether_forecasting.features import resample_1min
from noether_forecasting.protocol import ForecastResult


@dataclass
class PatchTSTForecaster:
    tag: str
    horizon_min: int = 30
    model_version: str = "patchtst-v0"
    model_kind: str = "patchtst"

    # CPU-friendly hyperparameters. Documented in libs/forecasting/README.md.
    input_size: int = 60
    n_heads: int = 4
    patch_len: int = 16
    stride: int = 8
    max_steps: int = 100
    batch_size: int = 32

    _nf: object | None = None
    _residual_std: float = 0.0
    _last_train_ds: pd.Timestamp | None = None
    _hyperparams: dict = field(default_factory=dict)

    def fit(self, series_train: pd.Series, series_val: pd.Series) -> None:
        # Lazy import — torch is heavy and we want it loaded only when this
        # forecaster is actually fitting. Keeps `import noether_forecasting`
        # cheap for the rest of the codebase.
        from neuralforecast import NeuralForecast
        from neuralforecast.losses.pytorch import MAE
        from neuralforecast.models import PatchTST

        train_1min = resample_1min(series_train).dropna()
        df = pd.DataFrame(
            {
                "unique_id": self.tag,
                "ds": train_1min.index,
                "y": train_1min.values,
            }
        )
        # NeuralForecast requires tz-naive ds.
        df["ds"] = df["ds"].dt.tz_localize(None)

        model = PatchTST(
            h=self.horizon_min,
            input_size=self.input_size,
            n_heads=self.n_heads,
            patch_len=self.patch_len,
            stride=self.stride,
            max_steps=self.max_steps,
            batch_size=self.batch_size,
            scaler_type="standard",
            loss=MAE(),
            random_seed=42,
            enable_progress_bar=False,
            logger=False,
        )
        nf = NeuralForecast(models=[model], freq="1min")
        nf.fit(df=df)
        self._nf = nf
        self._last_train_ds = pd.Timestamp(df["ds"].iloc[-1])
        self._hyperparams = {
            "input_size": self.input_size,
            "n_heads": self.n_heads,
            "patch_len": self.patch_len,
            "stride": self.stride,
            "max_steps": self.max_steps,
            "batch_size": self.batch_size,
        }

        # Compute a residual std on the validation series for the prediction
        # interval. We do a rolling 1-step walk-forward on the val window.
        val_1min = resample_1min(series_val).dropna()
        if len(val_1min) > self.input_size + self.horizon_min:
            preds = self._predict_horizon_array(val_1min.iloc[: self.input_size])
            target = val_1min.iloc[self.input_size : self.input_size + self.horizon_min].values
            n = min(len(preds), len(target))
            if n > 1:
                self._residual_std = float(np.std(preds[:n] - target[:n], ddof=1))

    def _predict_horizon_array(self, context: pd.Series) -> np.ndarray:
        """Internal: produce h forecasts from a context window."""
        if self._nf is None:
            raise RuntimeError("model is not fitted or loaded")
        ctx = pd.DataFrame(
            {
                "unique_id": self.tag,
                "ds": (
                    pd.DatetimeIndex(context.index).tz_localize(None)
                    if context.index.tz is not None
                    else context.index
                ),
                "y": context.values,
            }
        )
        out = self._nf.predict(df=ctx)
        # PatchTST output column is the model name "PatchTST"
        col = "PatchTST" if "PatchTST" in out.columns else out.columns[-1]
        return out[col].to_numpy()

    def predict(self, series: pd.Series) -> ForecastResult:
        """Forecast `horizon_min` steps ahead from the tail of `series`."""
        s = resample_1min(series).dropna()
        if len(s) < self.input_size:
            raise ValueError(
                f"context too short: need >={self.input_size} 1-min samples, got {len(s)}"
            )
        ctx = s.iloc[-self.input_size :]
        h_steps = self._predict_horizon_array(ctx)
        # The "point" at the requested horizon is the last forecast step.
        point = float(h_steps[-1])
        half = 1.96 * self._residual_std
        return ForecastResult(
            tag=self.tag,
            horizon_min=self.horizon_min,
            point=point,
            lower=point - half,
            upper=point + half,
            model_version=self.model_version,
            model_kind="patchtst",
        )

    def predict_batch(self, series: pd.Series, eval_index: pd.DatetimeIndex) -> np.ndarray:
        """Predict horizon-ahead values at each timestamp in `eval_index`.

        Walk-forward: for each `t`, use the `input_size` minutes ending at `t`
        as context and take the last step of the h-horizon forecast.
        """
        s = resample_1min(series).dropna()
        out = np.empty(len(eval_index), dtype=np.float64)
        for i, t in enumerate(eval_index):
            t_naive = t.tz_localize(None) if t.tzinfo is not None else t
            window_end = t_naive
            window_start = window_end - pd.Timedelta(minutes=self.input_size)
            s_naive_idx = s.index.tz_localize(None) if s.index.tz is not None else s.index
            mask = (s_naive_idx > window_start) & (s_naive_idx <= window_end)
            ctx = s[mask]
            if len(ctx) < self.input_size:
                # Edge case at the start of the eval window — fill with NaN.
                out[i] = np.nan
                continue
            ctx = ctx.iloc[-self.input_size :]
            h_steps = self._predict_horizon_array(ctx)
            out[i] = float(h_steps[-1])
        return out

    def save(self, path: Path) -> None:
        if self._nf is None:
            raise RuntimeError("nothing to save")
        path.parent.mkdir(parents=True, exist_ok=True)
        # NeuralForecast objects are joblib-pickleable. We bundle them with
        # our metadata so load() round-trips cleanly.
        joblib.dump(
            {
                "tag": self.tag,
                "horizon_min": self.horizon_min,
                "model_version": self.model_version,
                "nf": self._nf,
                "residual_std": self._residual_std,
                "last_train_ds": self._last_train_ds,
                "hyperparams": self._hyperparams,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> PatchTSTForecaster:
        bundle = joblib.load(path)
        hp = bundle.get("hyperparams", {})
        f = cls(
            tag=bundle["tag"],
            horizon_min=bundle["horizon_min"],
            model_version=bundle["model_version"],
            input_size=hp.get("input_size", 60),
            n_heads=hp.get("n_heads", 4),
            patch_len=hp.get("patch_len", 16),
            stride=hp.get("stride", 8),
            max_steps=hp.get("max_steps", 100),
            batch_size=hp.get("batch_size", 32),
        )
        f._nf = bundle["nf"]
        f._residual_std = bundle["residual_std"]
        f._last_train_ds = bundle.get("last_train_ds")
        f._hyperparams = hp
        return f
