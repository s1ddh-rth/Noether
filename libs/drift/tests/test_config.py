"""DriftConfig / load_drift_config + the committed evidently/config.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest
from noether_drift import DriftConfig, load_drift_config
from pydantic import ValidationError

REPO_CONFIG = Path(__file__).resolve().parents[3] / "evidently" / "config.yaml"


def test_load_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "reference_window_hours: 12\ncurrent_window_hours: 2\ntags: [A, B]\n",
        encoding="utf-8",
    )
    cfg = load_drift_config(p)
    assert cfg.reference_window_hours == 12.0
    assert cfg.current_window_hours == 2.0
    assert cfg.tags == ["A", "B"]
    # Unspecified keys fall back to model defaults.
    assert cfg.drift_share_threshold == 0.5
    assert cfg.min_rows == 30


def test_tags_required(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("reference_window_hours: 5\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_drift_config(p)


def test_threshold_bounds() -> None:
    with pytest.raises(ValidationError):
        DriftConfig(tags=["A"], drift_share_threshold=1.5)


def test_committed_repo_config_is_valid() -> None:
    """The shipped evidently/config.yaml must load + validate as-is."""
    cfg = load_drift_config(REPO_CONFIG)
    assert cfg.tags  # non-empty (min_length=1 enforced)
    assert 0.0 <= cfg.drift_share_threshold <= 1.0
    assert cfg.current_window_hours <= cfg.reference_window_hours
