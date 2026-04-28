"""SHAP-based per-tag attribution for an anomaly alert.

Strategy: for the Isolation Forest member, we use SHAP's TreeExplainer
to get exact per-tag contributions. For Mahalanobis and EWMA we use the
analytic per-tag breakdown from each detector. The final per-tag
contribution is a max-magnitude blend across detectors, normalised so
the absolute contributions sum to the alert score within ±5% as required
by the capability spec.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap
from pydantic import BaseModel

from noether_anomaly.detectors import (
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)
from noether_anomaly.ensemble import AnomalyEnsemble


class TagContribution(BaseModel):
    tag: str
    contribution: float


@dataclass
class Explainer:
    ensemble: AnomalyEnsemble

    def explain(self, X: pd.DataFrame, *, alert_score: float) -> list[TagContribution]:
        """Return per-tag contributions for the given window, sorted desc.

        The sum of |contribution_i| across tags is rescaled to equal
        `alert_score` so downstream consumers can render relative
        attribution without normalising again.
        """
        per_det_contribs: list[pd.Series] = []

        for det in self.ensemble.detectors:
            if isinstance(det, IsolationForestDetector):
                # SHAP TreeExplainer — pyod's IForest exposes .estimators_
                # via its sklearn-backed model attribute.
                inner = det._model
                if inner is None or not hasattr(inner, "estimators_"):
                    contrib = det.per_tag_contribution(X).iloc[-1]
                else:
                    explainer = shap.TreeExplainer(inner.detector_)
                    sv = explainer.shap_values(X[det._feature_cols].to_numpy(dtype=np.float64))
                    sv_arr = sv if isinstance(sv, np.ndarray) else np.asarray(sv)
                    # Aggregate across all rows in the window — last row's SHAP
                    # is most representative of "now"; we take its absolute
                    # magnitude so contributions can be ranked.
                    contrib = pd.Series(np.abs(sv_arr[-1]), index=det._feature_cols)
            elif isinstance(det, (MahalanobisDetector, EWMADetector)):
                contrib = det.per_tag_contribution(X).iloc[-1].abs()
            else:
                # Unknown detector — skip rather than fail open.
                continue

            # Normalise within detector to [0, 1] before blending.
            total = float(contrib.sum())
            if total > 0:
                contrib = contrib / total
            per_det_contribs.append(contrib)

        if not per_det_contribs:
            return []

        # Cross-detector blend: max-magnitude wins per tag (mirrors the
        # ensemble's max-of-detectors scoring).
        blended = pd.concat(per_det_contribs, axis=1).max(axis=1).fillna(0.0)
        blended = blended / max(blended.sum(), 1e-9) * alert_score

        ranked = sorted(
            (TagContribution(tag=k, contribution=float(v)) for k, v in blended.items()),
            key=lambda t: abs(t.contribution),
            reverse=True,
        )
        return ranked
