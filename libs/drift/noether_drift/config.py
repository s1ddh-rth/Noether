"""Drift job configuration.

Two layers:

- `DriftConfig` — the *analytical* definition (windows, tags, threshold).
  Canonical source is `evidently/config.yaml` so the reference-window
  definition is reviewable and lives next to the code (proposal task
  4.1). Loaded via `load_drift_config`.
- `DriftSettings` — *operational* knobs (where to write, how often)
  via `pydantic-settings`, env-overridable like every other service.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default reference-window definition path (repo-root relative). In
# containers the file is COPYed to /app/evidently/config.yaml.
DEFAULT_CONFIG_PATH = "evidently/config.yaml"


class DriftConfig(BaseModel):
    """Reference/current window definition + drift gate."""

    # The reference baseline is the `reference_window_hours` of data
    # immediately preceding the current window. The current window is the
    # most recent `current_window_hours`.
    reference_window_hours: PositiveFloat = Field(default=24.0)
    current_window_hours: PositiveFloat = Field(default=1.0)
    tags: list[str] = Field(min_length=1)
    # Dataset-level drift is declared when the share of drifted columns
    # exceeds this threshold (Evidently's own default is 0.5).
    drift_share_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    # Below this many rows in either window the run is recorded as
    # `insufficient_data` rather than producing a misleading verdict.
    min_rows: PositiveInt = Field(default=30)


class DriftSettings(BaseSettings):
    """Operational settings (paths, cadence, DB)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    config_path: str = Field(default=DEFAULT_CONFIG_PATH, alias="DRIFT_CONFIG")
    output_dir: str = Field(default="/drift-reports", alias="DRIFT_OUTPUT_DIR")
    # Used only by the compose `cron` loop wrapper; the job itself is
    # one-shot (Helm runs it as a CronJob).
    interval_s: PositiveInt = Field(default=3600, alias="DRIFT_INTERVAL_S")


def load_drift_config(path: str | Path | None = None) -> DriftConfig:
    """Load + validate the reference-window definition from YAML.

    Falls back to `DriftConfig` defaults for any key the file omits;
    `tags` is required (no sensible default for an arbitrary plant).
    """
    p = Path(path or DEFAULT_CONFIG_PATH)
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return DriftConfig(**raw)
