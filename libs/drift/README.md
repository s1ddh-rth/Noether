# noether-drift

Evidently-based input-drift monitoring (SPEC component 8 "Ops" /
add-ops-stack task 4).

## What it does

A **one-shot** job that:

1. Reads the reference-window definition from `evidently/config.yaml`
   (`DriftConfig`).
2. Pulls two windows from TimescaleDB via `noether_storage.query.pivot`
   — the most recent `current_window_hours`, and the
   `reference_window_hours` immediately before it.
3. Runs Evidently's `DataDriftPreset`.
4. Writes the full report JSON to `DRIFT_OUTPUT_DIR` (`drift-<ts>.json`
   + `latest.json`) and a compact summary row to the `drift_reports`
   table — which Grafana charts via the existing TimescaleDB datasource
   (no extra exporter).

Below `min_rows` in either window the run is recorded as
`insufficient_data` and exits non-zero so a scheduler surfaces it.

## Scheduling

The job is deliberately one-shot; scheduling is external:

- **compose**: `cron` profile loops it (`docker compose --profile cron up -d`)
  or run once with `make drift`.
- **Helm**: a `CronJob` (`drift.enabled`, `drift.schedule`).

## Config / env

| Var | Default | Meaning |
|-----|---------|---------|
| `DRIFT_CONFIG` | `evidently/config.yaml` | reference-window definition |
| `DRIFT_OUTPUT_DIR` | `/drift-reports` | report JSON volume |
| `DRIFT_INTERVAL_S` | `3600` | compose loop sleep only |
| `POSTGRES_*` | see `noether_storage` | Timescale connection |

## Test

```bash
uv run pytest libs/drift -q
```

Pure helpers (`window_bounds`, `extract_summary`, `load_drift_config`)
and the insufficient-data path are unit-tested without a DB or Evidently
(Evidently is imported lazily, only when there is data to evaluate).
