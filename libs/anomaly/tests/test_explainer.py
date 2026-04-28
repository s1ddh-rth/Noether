import pandas as pd
from noether_anomaly import (
    AnomalyEnsemble,
    EWMADetector,
    Explainer,
    IsolationForestDetector,
    MahalanobisDetector,
    TagContribution,
)


def test_explain_returns_ranked_contributions(
    baseline_panel: pd.DataFrame, faulty_panel: pd.DataFrame
) -> None:
    ens = AnomalyEnsemble(
        detectors=[
            IsolationForestDetector(n_estimators=50),
            MahalanobisDetector(),
            EWMADetector(),
        ]
    )
    ens.fit(baseline_panel)
    result = ens.score(faulty_panel.iloc[-120:])

    contribs = Explainer(ensemble=ens).explain(faulty_panel.iloc[-120:], alert_score=result.score)
    assert all(isinstance(c, TagContribution) for c in contribs)
    # Sorted by |contribution| descending.
    abs_vals = [abs(c.contribution) for c in contribs]
    assert abs_vals == sorted(abs_vals, reverse=True)


def test_explain_top_tag_is_the_perturbed_one(
    baseline_panel: pd.DataFrame, faulty_panel: pd.DataFrame
) -> None:
    ens = AnomalyEnsemble(
        detectors=[
            IsolationForestDetector(n_estimators=100),
            MahalanobisDetector(),
            EWMADetector(),
        ]
    )
    ens.fit(baseline_panel)
    window = faulty_panel.iloc[-120:]
    result = ens.score(window)
    contribs = Explainer(ensemble=ens).explain(window, alert_score=result.score)

    # The fault was injected onto X_0 — it must rank in the top 2 contributors.
    top_two = {contribs[0].tag, contribs[1].tag} if len(contribs) >= 2 else {contribs[0].tag}
    assert "X_0" in top_two


def test_explain_score_sum_within_tolerance(
    baseline_panel: pd.DataFrame, faulty_panel: pd.DataFrame
) -> None:
    """Capability spec says |contributions|.sum() ≈ alert score within ±5%."""
    ens = AnomalyEnsemble(
        detectors=[IsolationForestDetector(n_estimators=50), MahalanobisDetector(), EWMADetector()]
    )
    ens.fit(baseline_panel)
    window = faulty_panel.iloc[-120:]
    result = ens.score(window)
    contribs = Explainer(ensemble=ens).explain(window, alert_score=result.score)
    total = sum(abs(c.contribution) for c in contribs)
    # Tolerate a ±5% band.
    assert abs(total - result.score) <= 0.05 * max(result.score, 1e-9)
