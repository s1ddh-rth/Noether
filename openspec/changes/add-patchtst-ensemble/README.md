# add-patchtst-ensemble

Closes the deferred half of `add-forecasting-service` — adds PatchTST
(via Nixtla `neuralforecast`) and an LGBM/PatchTST ensemble to the
forecasting library, the inference service, and the eval harness.

- proposal.md — why and what
- design.md — Forecaster Protocol, registry dispatch, ensemble weighting
- tasks.md — implementation plan
- specs/forecasting-service/spec.md — MODIFIED requirement deltas
