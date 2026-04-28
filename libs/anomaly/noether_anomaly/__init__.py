"""Multivariate anomaly detection for plant tag windows.

Public API:
    AnomalyResult       — per-window scoring envelope
    Detector            — Protocol any detector conforms to
    IsolationForestDetector
    MahalanobisDetector
    EWMADetector
    AnomalyEnsemble     — combines detectors with rank-normalised scores
    Explainer           — produces per-tag contributions for an alert
"""

from noether_anomaly.detectors import (
    Detector,
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)
from noether_anomaly.ensemble import AnomalyEnsemble, AnomalyResult, DetectorBreakdown
from noether_anomaly.explainer import Explainer, TagContribution

__all__ = [
    "AnomalyEnsemble",
    "AnomalyResult",
    "Detector",
    "DetectorBreakdown",
    "EWMADetector",
    "Explainer",
    "IsolationForestDetector",
    "MahalanobisDetector",
    "TagContribution",
]
