# noether-ingest

Wire schema and synthetic generators for plant tag streams.

## Public API

- `TagSample` — pydantic model for one sensor reading. UTC-coerced timestamps; rejects NaN/Inf.
- `Quality` — enum: `good`, `bad`, `uncertain`.
- `Generator` — protocol any tag-stream source must implement.
- `SyntheticTEP` — deterministic TEP-shaped generator with fault injection
  (`none`, `step`, `drift`, `spike`).
- `TAG_NAMES` — ordered list of `XMEAS_1..41` + `XMV_1..11`.

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
