# noether-anomaly

Multivariate anomaly detection: PyOD-backed ensemble + EWMA control chart
+ SHAP explainer.

## Detectors

| Class | Backed by | Strength |
|---|---|---|
| `IsolationForestDetector` | PyOD `IForest` | wide-coverage, low false-positive on randomly scattered outliers |
| `MahalanobisDetector` | PyOD `MCD` (robust covariance) | catches subtle multivariate shifts even when each tag is in-band |
| `EWMADetector` | hand-rolled control chart | catches drift and small persistent mean shifts |

Each conforms to a `Detector` Protocol: `fit(X)`, `score(X)`,
`per_tag_contribution(X)`.

> **Note**: a torch-backed AutoEncoder detector named in the
> `add-anomaly-detection` spec is deferred to a follow-up. The three above
> cover the major TEP fault families (mean shift, drift, intermittent
> spikes) without bringing PyTorch into the AD path.

## Ensemble

`AnomalyEnsemble.fit(X)` fits every detector on a clean baseline window
and caches per-detector training scores for rank-normalisation. `score(X)`
returns an `AnomalyResult`:

```python
AnomalyResult(
    score=0.83,                          # rank-normalised, max across detectors
    detectors=DetectorBreakdown(
        iforest=0.71, mahalanobis=0.83, ewma=0.42
    ),
    tags=["XMEAS_1", ..., "XMV_11"],
    alert=True,                           # score >= ensemble.threshold
)
```

## SHAP-based explanation

`Explainer(ensemble).explain(window, alert_score=...)` returns a ranked
list of `(tag, contribution)`. Isolation Forest contributions come from
`shap.TreeExplainer`; Mahalanobis and EWMA use analytic per-tag breakdowns.
Contributions are rescaled so their sum equals the alert score within ±5%
(matches the capability spec scenario in
`openspec/changes/add-anomaly-detection/specs/anomaly-detection/spec.md`).

## Tests

```
uv run pytest libs/anomaly
```
