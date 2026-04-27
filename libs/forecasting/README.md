# noether-forecasting

LightGBM baseline forecaster + feature engineering. PatchTST and the ensemble
land in a later change proposal.

## Quick train

```
python -m noether_forecasting.training \
    --tag XMEAS_1 --horizon 30 --output ./models/xmeas_1.lgbm
```

Prints `{"tag":"XMEAS_1","mae":...,"rmse":...}` on success.

## At inference time

```python
from pathlib import Path
from noether_forecasting import LightGBMForecaster

model = LightGBMForecaster.load(Path("./models/xmeas_1.lgbm"))
result = model.predict(X_window)
```

`ForecastResult` carries `point`, `lower`, `upper`, `horizon_min`, `model_version`.
The interval is a crude `±1.96σ` of the validation residuals; quantile
regression / conformal will replace this in a follow-up.
