"""Synthetic plant-tag generators.

We expose a `Generator` Protocol so the real Tennessee Eastman simulator
(Fortran-via-f2py) can be swapped in later via its own change proposal
without touching downstream code.

The default `SyntheticTEP` produces dynamics that are *plausible* — slow
drifts, daily seasonality, correlated noise, and labelable fault profiles —
but it is NOT the real TEP. It is enough to demo ingest → storage → forecast
on a laptop without depending on a Fortran toolchain.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import numpy as np

# Tag layout matches the Tennessee Eastman Process: 41 measurements + 11
# manipulated variables. Names mirror the canonical TEP convention.
TAG_NAMES: list[str] = [f"XMEAS_{i}" for i in range(1, 42)] + [f"XMV_{i}" for i in range(1, 12)]


class Generator(Protocol):
    """Source of `(tag, value)` pairs at a single simulated timestep."""

    @property
    def tag_names(self) -> list[str]: ...
    def step(self) -> dict[str, float]: ...
    def reset(self) -> None: ...


@dataclass
class SyntheticTEP:
    """Deterministic TEP-shaped synthetic generator.

    Produces correlated, drifting, mildly noisy time series with optional
    fault injection. Seed-stable across reset()/step() pairs so eval runs
    are reproducible.

    fault_profile values:
        - "none"   : nominal operation
        - "step"   : abrupt mean shift on a subset of XMEAS at fault_start_s
        - "drift"  : slow linear drift
        - "spike"  : intermittent narrow spikes
    """

    seed: int = 42
    fault_profile: str = "none"
    fault_start_s: int = 0
    dt_seconds: float = 1.0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._t: int = 0
        self._n = len(TAG_NAMES)
        # Per-tag baselines drawn once. Different scales mimic flow,
        # temperature, pressure ranges across the TEP variable list.
        scale_pool = self._rng.uniform(0.5, 200.0, size=self._n)
        self._baseline = self._rng.uniform(-50.0, 250.0, size=self._n) * (
            scale_pool / scale_pool.max()
        )
        self._amp_daily = self._rng.uniform(0.5, 5.0, size=self._n)
        self._amp_noise = self._rng.uniform(0.05, 0.5, size=self._n)
        self._phase = self._rng.uniform(0.0, 2 * np.pi, size=self._n)
        # AR(1) noise state for temporal correlation
        self._ar_state = np.zeros(self._n, dtype=np.float64)

    @property
    def tag_names(self) -> list[str]:
        return list(TAG_NAMES)

    def reset(self) -> None:
        self.__post_init__()

    def step(self) -> dict[str, float]:
        t = self._t * self.dt_seconds
        # Slow daily seasonality + AR(1) coloured noise
        seasonal = self._amp_daily * np.sin(2 * np.pi * t / 86400.0 + self._phase)
        white = self._rng.standard_normal(self._n)
        self._ar_state = 0.85 * self._ar_state + self._amp_noise * white
        values = self._baseline + seasonal + self._ar_state

        if self.fault_profile != "none" and t >= self.fault_start_s:
            values = self._apply_fault(values, t)

        self._t += 1
        return {name: float(v) for name, v in zip(TAG_NAMES, values, strict=True)}

    def _apply_fault(self, values: np.ndarray, t: float) -> np.ndarray:
        # Faults touch the first ten XMEAS only — leaves XMV "manipulated"
        # variables clean, mirroring TEP fault patterns where measurements
        # diverge while controllers compensate.
        idx = slice(0, 10)
        elapsed = t - self.fault_start_s
        if self.fault_profile == "step":
            values[idx] = values[idx] + 5.0
        elif self.fault_profile == "drift":
            values[idx] = values[idx] + 0.001 * elapsed
        elif self.fault_profile == "spike" and int(elapsed) > 0 and int(elapsed) % 60 == 0:
            values[idx] = values[idx] + self._rng.uniform(10.0, 20.0)
        return values


def stream_samples(
    gen: Generator,
    *,
    start: datetime | None = None,
    dt: timedelta = timedelta(seconds=1),
) -> Iterator[tuple[datetime, dict[str, float]]]:
    """Yield (timestamp, sample-dict) pairs forever.

    Useful for offline training data generation; the live replayer drives
    its own loop with rate limiting.
    """
    ts = start or datetime.now(tz=UTC)
    while True:
        yield ts, gen.step()
        ts = ts + dt
