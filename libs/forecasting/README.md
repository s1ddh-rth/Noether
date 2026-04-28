# noether-forecasting

LightGBM + PatchTST + ensemble forecasters with a small feature-engineering
layer and a synthetic offline data generator for training.

## Models

| Class | Input at predict time | Artefact ext |
|---|---|---|
| `LightGBMForecaster` | feature DataFrame from `build_features` | `.lgbm` |
| `PatchTSTForecaster` | raw 1-Hz / 1-min series | `.patchtst` |
| `EnsembleForecaster` | both (X + series) | `.ensemble` |

All three carry `tag`, `horizon_min`, `model_version`, `model_kind`, plus
`save(path)` / `load(path)`. The inference service's `ModelRegistry` resolves
`<tag>.{ensemble,patchtst,lgbm}` in priority order — drop a `.ensemble`
artefact in `MODEL_DIR` and `/forecast` automatically prefers it.

## Train one tag

```
# LightGBM only (M1 baseline)
python -m noether_forecasting.training --tag XMEAS_1 --output models/xmeas_1.lgbm

# PatchTST (CPU; ~30 s with default --max-steps 100)
python -m noether_forecasting.training --tag XMEAS_1 --model patchtst --output models/xmeas_1.patchtst

# Ensemble — also writes the two member artefacts alongside
python -m noether_forecasting.training --tag XMEAS_1 --model ensemble --output models/xmeas_1.ensemble
```

Each prints a one-line JSON with metrics or weights on success.

## PatchTST hyperparameters

CPU-friendly defaults are baked into `PatchTSTForecaster`:

| Hyperparameter | Default | Why |
|---|---|---|
| `input_size` | 60 | 1-hour context window |
| `n_heads` | 4 | small attention budget |
| `patch_len` | 16 | Nixtla tutorial recipe |
| `stride` | 8 | half-overlap |
| `max_steps` | 100 | CPU budget — bumps quality with larger numbers |
| `batch_size` | 32 | safe on small RAM |

The training CLI takes `--max-steps`. Increase for production-grade runs;
the eval harness uses `--max-steps 100` by default.

## Eval harness

```
python -m eval.forecast_harness                  # all four models, --hours 168
python -m eval.forecast_harness --skip patchtst  # smoke: naive + LGBM only
python -m eval.forecast_harness --skip ensemble  # naive + LGBM + PatchTST
```

Writes `eval/results/forecast.json` with a `skipped` field and per-tag
per-model `mae` / `rmse` / `smape`. The harness exits non-zero if any tag
is missing any non-skipped model — this matches the
`forecasting-service` capability scenario.

## At inference time

```python
from pathlib import Path
from noether_forecasting import (
    LightGBMForecaster, PatchTSTForecaster, EnsembleForecaster,
)

ens = EnsembleForecaster.load(Path("models/xmeas_1.ensemble"))
result = ens.predict(X_window, series_window)
print(result.point, result.model_kind, ens.weight_lgbm, ens.weight_patchtst)
```
