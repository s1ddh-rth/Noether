import numpy as np
import pandas as pd
import pytest

from noether_anomaly import (
    Detector,
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: IsolationForestDetector(n_estimators=50),
        lambda: MahalanobisDetector(),
        lambda: EWMADetector(),
    ],
    ids=["iforest", "mahalanobis", "ewma"],
)
def test_detector_protocol_conformance(factory) -> None:
    det = factory()
    assert isinstance(det, Detector)
    assert det.name


def test_iforest_separates_baseline_from_faulty(
    baseline_panel: pd.DataFrame, faulty_panel: pd.DataFrame
) -> None:
    det = IsolationForestDetector(n_estimators=100)
    det.fit(baseline_panel)
    baseline_score = det.score(baseline_panel).mean()
    faulty_late = det.score(faulty_panel.iloc[len(faulty_panel) // 2 :]).mean()
    assert faulty_late > baseline_score


def test_mahalanobis_score_monotonic_in_squared_distance(
    baseline_panel: pd.DataFrame,
) -> None:
    """PyOD's MCD score is the Mahalanobis distance; our per-tag contribution
    rows sum to the squared distance. The two should be monotonic — checked
    via Spearman's rank correlation rather than Pearson, which is robust to
    the sqrt non-linearity.
    """
    from scipy.stats import spearmanr

    det = MahalanobisDetector()
    det.fit(baseline_panel)
    raw = det.score(baseline_panel)
    rowsum = det.per_tag_contribution(baseline_panel).sum(axis=1).to_numpy()
    rho, _ = spearmanr(raw, rowsum)
    assert rho > 0.95


def test_ewma_flags_step_shift(baseline_panel: pd.DataFrame, faulty_panel: pd.DataFrame) -> None:
    det = EWMADetector(lam=0.2, k_sigma=3.0)
    det.fit(baseline_panel)
    # Score the full faulty panel — last half should produce far higher z than baseline.
    z_faulty = det.score(faulty_panel)
    half = len(faulty_panel) // 2
    assert z_faulty[half + 30 :].mean() > z_faulty[:half].mean()


def test_unfitted_detectors_raise() -> None:
    with pytest.raises(RuntimeError):
        IsolationForestDetector().score(pd.DataFrame({"a": [1.0]}))
    with pytest.raises(RuntimeError):
        MahalanobisDetector().score(pd.DataFrame({"a": [1.0]}))
    with pytest.raises(RuntimeError):
        EWMADetector().score(pd.DataFrame({"a": [1.0]}))


def test_per_tag_contribution_shape(baseline_panel: pd.DataFrame) -> None:
    for det in (IsolationForestDetector(n_estimators=20), MahalanobisDetector(), EWMADetector()):
        det.fit(baseline_panel)
        contrib = det.per_tag_contribution(baseline_panel.iloc[:50])
        assert contrib.shape == (50, baseline_panel.shape[1])
        assert list(contrib.columns) == list(baseline_panel.columns)
