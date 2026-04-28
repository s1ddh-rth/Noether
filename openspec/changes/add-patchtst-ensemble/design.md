## Goals

- Match the existing `forecasting-service` capability spec exactly: train
  LGBM + PatchTST + ensemble; eval reports naive / LGBM / PatchTST /
  ensemble × MAE / RMSE / SMAPE.
- Keep the inference image runnable on the same hardware the M1 stack
  fits on (≤ 6 GB Docker RAM).
- Preserve the M1 Forecaster surface: `LightGBMForecaster.predict(X)` and
  any new model expose the same `ForecastResult` shape so the router can
  call them uniformly.

## Non-Goals

- GPU / CUDA support. Per SPEC section 9: laptop / k3s only.
- Continual / online learning. Out of scope for v0.1.
- Distillation, quantization, ONNX export. Pre-mature for v0.1.
- Anything that requires Hugging Face Hub or torchvision-style downloads
  at runtime — air-gap rule (SPEC section 5).

## Key Decisions

### Decision: keep `Forecaster` as a Protocol, not an ABC
`libs/forecasting/protocol.py` introduces:

```python
class Forecaster(Protocol):
    tag: str
    horizon_min: int
    model_version: str
    def fit(self, X_tr, y_tr, X_va, y_va) -> None: ...
    def predict(self, X) -> ForecastResult: ...
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "Forecaster": ...
```

LightGBM, PatchTST, and the ensemble all conform structurally. We avoid
nominal inheritance because PatchTST's underlying `NeuralForecast` object
already carries its own typing.

### Decision: artefact-extension keyed registry
`ModelRegistry.get(tag)` resolves `<MODEL_DIR>/<tag>.{lgbm,patchtst,ensemble}`
by globbing for any of the three suffixes. If multiple exist, ensemble wins
over patchtst wins over lgbm. Artefacts include `model_kind` metadata so
the loader can dispatch without parsing extensions.

This is preferred over a manifest file because it stays
transparently editable from the host filesystem during dev.

### Decision: PatchTST hyperparameters
Defaults follow the Nixtla `neuralforecast` PatchTST tutorial values for
ETT-style univariate forecasting, scaled down for CPU:
- `h = horizon_min` (forecast steps after 1-min resampling)
- `input_size = 60` (one-hour context window)
- `n_heads = 4`, `patch_len = 16`, `stride = 8`
- `max_steps = 200` (CPU budget; tune via training CLI flag)

These are explicitly documented in `libs/forecasting/README.md` so
re-runs are reproducible.

### Decision: ensemble weights
Two-model convex combination with weights fitted by minimising MSE on the
validation fold (`scipy.optimize.minimize`, bounds `[0, 1]`, sum-to-one
constraint). Closed-form is also fine but the optimiser keeps the door
open for non-MSE losses later (pinball, asymmetric).

The fitted weights and validation MSE are stored in the ensemble artefact
so the eval harness can render `weight_lgbm` / `weight_patchtst` columns
in the benchmarks table.

### Decision: prediction interval
LGBM's residual-σ band stays. PatchTST exposes its own quantile predictions
when configured with `loss=DistributionLoss('Normal')` — we use those for
the PatchTST band. The ensemble's band is the convex combination of the
two model bands, which is a conservative approximation but avoids stacking
quantile regressors. Conformal calibration can replace this in a follow-up.

## Risks

- **Risk: image bloat.** torch CPU wheel is ~600 MB. SPEC section 11 (cost / size).
  - **Mitigation**: separate a `inference-light` stage that depends on
    only the LGBM serve path, pull torch into a `inference-full` stage
    behind a build arg. Default keeps full for now to satisfy SPEC
    section 10. Revisit if RAM headroom becomes an issue in CI.
- **Risk: PatchTST training instability on synthetic data.** The synthetic
  TEP signal is mostly seasonal + noise — PatchTST may fail to add real
  signal over LGBM, making the ensemble degrade to ~LGBM weight = 1.
  - **Mitigation**: that's an *honest* benchmark. Document in
    `docs/benchmarks.md`. The real TEP simulator switch (separate change)
    will give PatchTST something non-trivial to learn.
- **Risk: training time creep.** PatchTST CPU training is ~30 s/tag at
  `max_steps=200`. The eval harness retraining four-tag panels per CI run
  would be ~2 min, adding to overall test time.
  - **Mitigation**: harness gets a `--skip patchtst` flag that the smoke
    tests use. Real benchmark runs use full settings.
