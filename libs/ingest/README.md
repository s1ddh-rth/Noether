# noether-ingest

Wire schema and synthetic generators for plant tag streams.

## Public API

- `TagSample` — pydantic model for one sensor reading. UTC-coerced timestamps; rejects NaN/Inf.
- `Quality` — enum: `good`, `bad`, `uncertain`.
- `Generator` — protocol any tag-stream source must implement.
- `SyntheticTEP` — deterministic TEP-shaped generator with fault injection
  (`none`, `step`, `drift`, `spike`).
- `TAG_NAMES` — ordered list of `XMEAS_1..41` + `XMV_1..11`.
- `logging.configure(level, service)` — shared structlog JSON setup.
- `metrics.start_metrics_server(port, service)` — stands up the
  Prometheus exposition HTTP server for the worker services (ingest,
  storage-consumer, anomaly-detector), which have no HTTP framework of
  their own. Lives here for the same reason `logging` does: every
  service depends on this lib transitively.

## Why synthetic instead of real pyTEP

The real Tennessee Eastman simulator wraps Fortran via f2py, which is brittle
on Windows and adds a heavy build dependency for a v0.1 portfolio repo. The
generator behind a `Generator` protocol means a real-pyTEP swap is a contained
change later. SPEC section 6 still names TEP as the canonical dataset for the eval
harness; we'll plug the real simulator into the AD eval path in Milestone 2.

## Tests

```
pytest libs/ingest
```
