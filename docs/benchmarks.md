# Benchmarks

Updated by the eval harnesses. See SPEC §10 for the v0.1 bar.

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
Numbers below are rendered into this file by the eval CI job (out of scope
for M1; placeholder until that lands):

| tag | horizon | n_test | naive MAE | naive RMSE | LGBM MAE | LGBM RMSE |
|---|---|---|---|---|---|---|
| _pending first run_ | | | | | | |

## Anomaly Detection (M2)

_Placeholder — populated by `anomaly_harness.py` once M2 ships._

## RAG (M3)

_Placeholder — populated by `rag_ragas.py` once M3 ships._
