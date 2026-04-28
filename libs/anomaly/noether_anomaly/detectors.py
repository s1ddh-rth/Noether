"""Individual anomaly detectors.

Each conforms to a small `Detector` Protocol so the ensemble can treat
them uniformly. We rely on PyOD where it carries weight (Isolation
Forest, MCD-based Mahalanobis) and implement EWMA ourselves because PyOD
doesn't ship a streaming control-chart variant.

AutoEncoder is intentionally deferred to a follow-up — PyTorch is heavy
and the IF + Mahalanobis + EWMA trio gives strong coverage on the kinds
of faults TEP exhibits (mean shift, drift, intermittent spikes).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from pyod.models.mcd import MCD


@runtime_checkable
class Detector(Protocol):
    name: str

    def fit(self, X: pd.DataFrame) -> None: ...
    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Return one anomaly score per row in `X` (higher = more anomalous)."""
        ...

    def per_tag_contribution(self, X: pd.DataFrame) -> pd.DataFrame:
        """Per-row × per-tag breakdown of the score."""
        ...


# --------------------------------------------------------------------------
# Isolation Forest
# --------------------------------------------------------------------------


@dataclass
class IsolationForestDetector:
    """PyOD Isolation Forest. Treats each row as an independent observation."""

    name: str = "iforest"
    n_estimators: int = 200
    contamination: float = 0.05
    random_state: int = 42

    _model: IForest | None = None
    _feature_cols: list[str] = field(default_factory=list)

    def fit(self, X: pd.DataFrame) -> None:
        self._feature_cols = list(X.columns)
        self._model = IForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=1,
        )
        self._model.fit(X.to_numpy(dtype=np.float64))

    def score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("IsolationForestDetector not fitted")
        # PyOD's decision_function is "the higher the more normal" for IForest
        # internally, but `decision_scores_` and `decision_function` actually
        # return higher = more anomalous after PyOD's wrapping. We lean on
        # that convention.
        return np.asarray(
            self._model.decision_function(X[self._feature_cols].to_numpy(dtype=np.float64))
        )

    def per_tag_contribution(self, X: pd.DataFrame) -> pd.DataFrame:
        """Crude per-tag attribution via leave-one-feature-out delta.

        For each row, compute the score with each feature replaced by its
        training median; the delta ≈ that feature's contribution. SHAP-based
        attribution lives in `noether_anomaly.explainer.Explainer`.
        """
        if self._model is None:
            raise RuntimeError("IsolationForestDetector not fitted")
        median = X[self._feature_cols].median()
        baseline = self.score(X)
        rows = []
        for col in self._feature_cols:
            X_perturbed = X.copy()
            X_perturbed[col] = median[col]
            rows.append(baseline - self.score(X_perturbed))
        contrib = np.vstack(rows).T  # shape (n_rows, n_features)
        return pd.DataFrame(contrib, columns=self._feature_cols, index=X.index)


# --------------------------------------------------------------------------
# Mahalanobis (via robust MCD covariance)
# --------------------------------------------------------------------------


@dataclass
class MahalanobisDetector:
    """Robust Mahalanobis distance using a Minimum Covariance Determinant fit."""

    name: str = "mahalanobis"
    contamination: float = 0.05
    random_state: int = 42

    _model: MCD | None = None
    _feature_cols: list[str] = field(default_factory=list)
    _mean: np.ndarray | None = None
    _inv_cov: np.ndarray | None = None

    def fit(self, X: pd.DataFrame) -> None:
        self._feature_cols = list(X.columns)
        # MCD with 'support_fraction' default uses a robust subset.
        self._model = MCD(contamination=self.contamination, random_state=self.random_state)
        self._model.fit(X.to_numpy(dtype=np.float64))
        self._mean = self._model.location_.copy()
        # MCD exposes covariance_; invert for the Mahalanobis distance.
        cov = self._model.covariance_
        # Regularise — adds a tiny ridge to keep inversion stable on
        # near-rank-deficient panels.
        d = cov.shape[0]
        self._inv_cov = np.linalg.pinv(cov + 1e-9 * np.eye(d))

    def score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("MahalanobisDetector not fitted")
        return np.asarray(
            self._model.decision_function(X[self._feature_cols].to_numpy(dtype=np.float64))
        )

    def per_tag_contribution(self, X: pd.DataFrame) -> pd.DataFrame:
        """Per-tag squared Mahalanobis contribution.

        For diagonal-cov assumptions: c_i = (x_i - mu_i)^2 * inv_cov[i, i].
        We use the row-wise dot product to avoid the simplification.
        """
        if self._mean is None or self._inv_cov is None:
            raise RuntimeError("MahalanobisDetector not fitted")
        Xv = X[self._feature_cols].to_numpy(dtype=np.float64)
        diff = Xv - self._mean
        # Row-wise: contrib_ij = diff_ij * sum_k(inv_cov[i,k] * diff_ik)
        # which is the j-th term in (diff @ inv_cov @ diff.T) per row.
        intermediate = diff @ self._inv_cov  # (n, d)
        contrib = diff * intermediate  # element-wise; row sum == squared distance
        return pd.DataFrame(contrib, columns=self._feature_cols, index=X.index)


# --------------------------------------------------------------------------
# EWMA control chart
# --------------------------------------------------------------------------


@dataclass
class EWMADetector:
    """Per-tag exponentially-weighted-moving-average control chart.

    Score is the maximum across tags of |z_i - mu_i| / sigma_z_i, where
    sigma_z_i is the asymptotic EWMA standard deviation. Naturally handles
    drift and step changes; less sensitive to high-frequency noise than
    a fixed Z-score.
    """

    name: str = "ewma"
    lam: float = 0.2
    k_sigma: float = 3.0  # used by alert() — score function returns raw multiplier

    _feature_cols: list[str] = field(default_factory=list)
    _mu: np.ndarray | None = None
    _sigma: np.ndarray | None = None
    _sigma_z: np.ndarray | None = None

    def fit(self, X: pd.DataFrame) -> None:
        self._feature_cols = list(X.columns)
        Xv = X[self._feature_cols].to_numpy(dtype=np.float64)
        self._mu = Xv.mean(axis=0)
        self._sigma = Xv.std(axis=0, ddof=1)
        self._sigma[self._sigma < 1e-9] = 1e-9  # guard against zero-variance tags
        # Asymptotic EWMA standard deviation for stationary series.
        self._sigma_z = self._sigma * np.sqrt(self.lam / (2.0 - self.lam))

    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Compute EWMA series across the rows in X and return max-tag z-score per row."""
        if self._mu is None or self._sigma_z is None:
            raise RuntimeError("EWMADetector not fitted")
        Xv = X[self._feature_cols].to_numpy(dtype=np.float64)
        z = np.zeros_like(Xv)
        z[0] = self.lam * Xv[0] + (1 - self.lam) * self._mu
        for t in range(1, len(Xv)):
            z[t] = self.lam * Xv[t] + (1 - self.lam) * z[t - 1]
        normed = np.abs(z - self._mu) / self._sigma_z
        return normed.max(axis=1)

    def per_tag_contribution(self, X: pd.DataFrame) -> pd.DataFrame:
        if self._mu is None or self._sigma_z is None:
            raise RuntimeError("EWMADetector not fitted")
        Xv = X[self._feature_cols].to_numpy(dtype=np.float64)
        z = np.zeros_like(Xv)
        z[0] = self.lam * Xv[0] + (1 - self.lam) * self._mu
        for t in range(1, len(Xv)):
            z[t] = self.lam * Xv[t] + (1 - self.lam) * z[t - 1]
        normed = np.abs(z - self._mu) / self._sigma_z
        return pd.DataFrame(normed, columns=self._feature_cols, index=X.index)
