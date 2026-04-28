"""Ensemble scorer combining multiple detectors with rank-normalised scores.

We rank-normalise each detector's training-window scores so detectors that
output unbounded scales (Isolation Forest, Mahalanobis distance, EWMA z)
can be combined fairly. The final ensemble score is the max across
detectors of the rank-normalised score — a single hot detector is enough
to fire an alert, but the breakdown shows which one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel

from noether_anomaly.detectors import Detector


class DetectorBreakdown(BaseModel):
    """Per-detector contribution to a single ensemble score."""

    iforest: float = 0.0
    mahalanobis: float = 0.0
    ewma: float = 0.0


class AnomalyResult(BaseModel):
    score: float
    detectors: DetectorBreakdown
    tags: list[str]
    alert: bool


@dataclass
class AnomalyEnsemble:
    """Holds fitted detectors and rank-normalises their scores."""

    detectors: list[Detector] = field(default_factory=list)
    threshold: float = 0.7
    _train_scores: dict[str, np.ndarray] = field(default_factory=dict)
    _feature_cols: list[str] = field(default_factory=list)

    def fit(self, X: pd.DataFrame) -> None:
        self._feature_cols = list(X.columns)
        self._train_scores = {}
        for det in self.detectors:
            det.fit(X)
            # Cache training-window scores for rank normalisation.
            self._train_scores[det.name] = np.sort(det.score(X))

    def _rank_normalise(self, name: str, raw: np.ndarray) -> np.ndarray:
        """Map raw scores to [0, 1] via empirical CDF on the training window."""
        ref = self._train_scores.get(name)
        if ref is None or len(ref) == 0:
            return np.zeros_like(raw)
        # Right-tail CDF — fraction of training scores below each test score.
        return np.searchsorted(ref, raw, side="right") / len(ref)

    def score(self, X: pd.DataFrame) -> AnomalyResult:
        if not self.detectors:
            raise RuntimeError("ensemble has no detectors")
        breakdown_acc: dict[str, float] = {}
        normed_per_det: list[np.ndarray] = []
        for det in self.detectors:
            raw = det.score(X)
            normed = self._rank_normalise(det.name, raw)
            # The per-window score is the max over rows in the window —
            # one bad row is enough to make the window suspicious.
            window_score = float(np.max(normed))
            breakdown_acc[det.name] = window_score
            normed_per_det.append(normed)
        ensemble = float(max(breakdown_acc.values()))
        breakdown = DetectorBreakdown(
            iforest=breakdown_acc.get("iforest", 0.0),
            mahalanobis=breakdown_acc.get("mahalanobis", 0.0),
            ewma=breakdown_acc.get("ewma", 0.0),
        )
        return AnomalyResult(
            score=ensemble,
            detectors=breakdown,
            tags=list(self._feature_cols),
            alert=ensemble >= self.threshold,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "detectors": self.detectors,
                "threshold": self.threshold,
                "train_scores": self._train_scores,
                "feature_cols": self._feature_cols,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> AnomalyEnsemble:
        bundle = joblib.load(path)
        e = cls(detectors=bundle["detectors"], threshold=bundle["threshold"])
        e._train_scores = bundle["train_scores"]
        e._feature_cols = bundle["feature_cols"]
        return e
