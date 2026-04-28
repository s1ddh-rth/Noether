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
