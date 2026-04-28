import math

from noether_ingest import TAG_NAMES, SyntheticTEP


def test_step_yields_full_tag_set() -> None:
    gen = SyntheticTEP(seed=1)
    sample = gen.step()
    assert set(sample.keys()) == set(TAG_NAMES)
    assert all(math.isfinite(v) for v in sample.values())


def test_seed_determinism() -> None:
    a = SyntheticTEP(seed=7)
    b = SyntheticTEP(seed=7)
    series_a = [a.step() for _ in range(50)]
    series_b = [b.step() for _ in range(50)]
    assert series_a == series_b


def test_reset_restores_initial_state() -> None:
    gen = SyntheticTEP(seed=3)
    first = gen.step()
    gen.reset()
    after_reset = gen.step()
    assert first == after_reset


def test_step_fault_shifts_first_xmeas_band() -> None:
    nominal = SyntheticTEP(seed=11, fault_profile="none")
    faulty = SyntheticTEP(seed=11, fault_profile="step", fault_start_s=0)
    diffs = []
    for _ in range(60):
        n = nominal.step()
        f = faulty.step()
        diffs.append(f["XMEAS_1"] - n["XMEAS_1"])
    # Fault adds +5.0 to first ten XMEAS variables.
    assert all(abs(d - 5.0) < 1e-9 for d in diffs)
