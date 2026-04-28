# Benchmarks

Updated by the eval harnesses. See SPEC section 10 for the v0.1 bar.

## Forecast (M1)

The forecast harness runs:
- **naive**: last-observed-value baseline (`y_hat(t+h) = y(t)`)
- **LGBM**: LightGBM regressor with lag/rolling/seasonality features

Run locally:

```
make eval
# or:
python -m eval.forecast_harness --tags XMEAS_1 XMEAS_7 XMEAS_13 --horizon 30
```

The harness writes `eval/results/forecast.json` and prints a Markdown table.
First run, 2026-04-28, on the synthetic TEP panel (`--hours 48`, seed 42):

| tag | horizon | n_test | naive MAE | naive RMSE | LGBM MAE | LGBM RMSE |
|---|---|---|---|---|---|---|
| XMEAS_1  | 30m | 418 | 0.458 | 0.508 | 0.134 | 0.168 |
| XMEAS_7  | 30m | 418 | 0.296 | 0.342 | 0.111 | 0.140 |
| XMEAS_13 | 30m | 418 | 0.341 | 0.409 | 0.142 | 0.181 |

LightGBM beats the last-value baseline by ~2.5–3× on MAE across all three
tags — the slow seasonal + AR(1) dynamics give the lag/rolling features
real signal, but the noise floor keeps it from being trivial.

These numbers are from the synthetic generator. Once the real Tennessee
Eastman simulator lands (separate change proposal), this table will be
re-rendered against TEP variables on the same horizon.

## Anomaly Detection (M2)

The AD harness fits the 3-detector ensemble (Isolation Forest + Mahalanobis +
EWMA) on a clean baseline, then scores sliding 60-s windows across pre-fault
+ fault data and reports the best-F1 threshold per scenario.

```
python -m eval.anomaly_harness
# or in compose:
docker compose --profile eval run --rm anomaly-eval
```

First run, 2026-04-28, on the synthetic TEP panel (120 min pre-fault + 60 min
fault, 60-s windows with 5-s stride):

| fault_id | profile | best F1 | precision | recall | threshold | alerts / truth |
|---|---|---|---|---|---|---|
| 1 | step (+5.0)   | 0.999 | 1.000 | 0.999 | 0.918 | 719 / 720 |
| 2 | step (+10.0)  | 0.999 | 0.999 | 1.000 | 0.693 | 721 / 720 |
| 3 | drift (1e-3/s)| 0.993 | 0.986 | 1.000 | 0.541 | 730 / 720 |
| 4 | drift (5e-3/s)| 0.994 | 0.999 | 0.990 | 0.775 | 714 / 720 |
| 5 | spike (10–20) | 0.995 | 0.990 | 1.000 | 0.765 | 727 / 720 |
| 6 | spike (20–40) | 0.995 | 0.997 | 0.993 | 0.663 | 717 / 720 |

The strong-fault scenarios (1, 2, 5, 6) hit ≥0.995 F1 because the perturbed
XMEAS rows are far outside any rank in the training window — almost every
test row's rank-normalised score saturates at 1.0. The drift scenarios (3,
4) are the harder case because the shift accumulates slowly; the harness
finds the best operating threshold by sweep.

These scenarios stand in for real TEP fault IDs (1–21). When the
Fortran-backed Tennessee Eastman simulator drops in (separate change), the
fault profiles map onto canonical TEP IDs without changing the harness.

## RAG (M3)

_Placeholder — populated by `rag_ragas.py` once M3 ships._
