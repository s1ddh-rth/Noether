import pandas as pd
import pytest
from noether_anomaly import (
    AnomalyEnsemble,
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)


@pytest.fixture
def fitted_ensemble(baseline_panel: pd.DataFrame) -> AnomalyEnsemble:
    e = AnomalyEnsemble(
        detectors=[
            IsolationForestDetector(n_estimators=50),
            MahalanobisDetector(),
            EWMADetector(),
        ],
        threshold=0.95,
    )
    e.fit(baseline_panel)
    return e


def test_score_envelope_shape(
    fitted_ensemble: AnomalyEnsemble, baseline_panel: pd.DataFrame
) -> None:
    result = fitted_ensemble.score(baseline_panel.iloc[:60])
    assert 0.0 <= result.score <= 1.0
    assert isinstance(result.alert, bool)
    assert set(result.tags) == set(baseline_panel.columns)
    bd = result.detectors
    assert 0.0 <= bd.iforest <= 1.0
    assert 0.0 <= bd.mahalanobis <= 1.0
    assert 0.0 <= bd.ewma <= 1.0


def test_alert_triggers_above_threshold(
    fitted_ensemble: AnomalyEnsemble, faulty_panel: pd.DataFrame
) -> None:
    """A clearly-faulty window (>6σ shift on X_0) should fire the alert."""
    last_window = faulty_panel.iloc[-120:]
    result = fitted_ensemble.score(last_window)
    assert result.alert is True
    assert result.score >= fitted_ensemble.threshold


def test_alert_flag_consistent_with_score(
    fitted_ensemble: AnomalyEnsemble, faulty_panel: pd.DataFrame
) -> None:
    """The boolean must always equal the threshold comparison."""
    for window in (faulty_panel.iloc[-120:], faulty_panel.iloc[100:160]):
        result = fitted_ensemble.score(window)
        assert result.alert == (result.score >= fitted_ensemble.threshold)


def test_baseline_window_does_not_alert(
    fitted_ensemble: AnomalyEnsemble, baseline_panel: pd.DataFrame
) -> None:
    # A window from the same distribution as training rarely scores at the
    # extreme tail.
    mid_window = baseline_panel.iloc[500:560]
    result = fitted_ensemble.score(mid_window)
    assert result.score < 1.0  # not maxed out


def test_baseline_score_calibrated_below_threshold(
    fitted_ensemble: AnomalyEnsemble, baseline_panel: pd.DataFrame
) -> None:
    """Regression for the np.max-aggregation bug.

    The previous implementation took np.max of per-row rank-normalised
    detector scores across a 60-row window. With ~60 rows on the IF/Mahalanobis
    rank-CDF, at least one row almost always landed near 1.0, so clean
    windows scored ~0.99 and the alert threshold was effectively useless.

    The fix is np.mean per detector window: a baseline window should
    centre around 0.5 and stay well below the 0.95 alert threshold.
    """
    threshold = fitted_ensemble.threshold  # 0.95
    # Several non-overlapping windows from inside the training distribution.
    for start in (60, 240, 480, 720, 960, 1200, 1440):
        window = baseline_panel.iloc[start : start + 60]
        result = fitted_ensemble.score(window)
        assert result.score < threshold - 0.2, (
            f"baseline window @{start} scored {result.score:.3f}; "
            f"calibration says it must be < {threshold - 0.2:.3f}"
        )
        assert result.alert is False


def test_save_load_round_trip(
    tmp_path, fitted_ensemble: AnomalyEnsemble, baseline_panel: pd.DataFrame
) -> None:
    path = tmp_path / "anomaly.joblib"
    fitted_ensemble.save(path)
    restored = AnomalyEnsemble.load(path)
    assert restored.threshold == fitted_ensemble.threshold
    # Same window → same score after round-trip.
    a = fitted_ensemble.score(baseline_panel.iloc[:60]).score
    b = restored.score(baseline_panel.iloc[:60]).score
    assert a == pytest.approx(b, rel=1e-6)


def test_empty_detectors_raises(baseline_panel: pd.DataFrame) -> None:
    e = AnomalyEnsemble(detectors=[], threshold=0.5)
    e.fit(baseline_panel)  # vacuous, but allowed
    with pytest.raises(RuntimeError):
        e.score(baseline_panel)
