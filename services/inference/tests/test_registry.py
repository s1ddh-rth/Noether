"""ModelRegistry extension-priority dispatch."""

from pathlib import Path

import pytest

from noether_svc_inference.deps import ModelRegistry


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    d = tmp_path / "models"
    d.mkdir()
    return d


def _touch(p: Path) -> None:
    p.write_bytes(b"placeholder")


def test_known_tags_unions_across_kinds(model_dir: Path) -> None:
    _touch(model_dir / "xmeas_1.lgbm")
    _touch(model_dir / "xmeas_2.patchtst")
    _touch(model_dir / "xmeas_3.ensemble")
    reg = ModelRegistry(model_dir)
    assert reg.known_tags() == ["XMEAS_1", "XMEAS_2", "XMEAS_3"]


def test_known_tags_dedupes_when_multiple_kinds_for_same_tag(model_dir: Path) -> None:
    _touch(model_dir / "xmeas_1.lgbm")
    _touch(model_dir / "xmeas_1.patchtst")
    _touch(model_dir / "xmeas_1.ensemble")
    reg = ModelRegistry(model_dir)
    assert reg.known_tags() == ["XMEAS_1"]


def test_get_unknown_tag_raises(model_dir: Path) -> None:
    reg = ModelRegistry(model_dir)
    with pytest.raises(FileNotFoundError):
        reg.get("MISSING")


def test_known_tags_empty_dir(tmp_path: Path) -> None:
    reg = ModelRegistry(tmp_path / "does-not-exist")
    assert reg.known_tags() == []


def test_get_priority_ensemble_over_others(monkeypatch, model_dir: Path) -> None:
    """When a tag has all three kinds, ensemble must win."""
    _touch(model_dir / "xmeas_1.lgbm")
    _touch(model_dir / "xmeas_1.patchtst")
    _touch(model_dir / "xmeas_1.ensemble")

    loaded = []

    class FakeForecaster:
        @classmethod
        def load(cls, path: Path):
            loaded.append(path.suffix)
            return cls()

    # Patch the loaders so we don't actually deserialise joblib.
    from noether_svc_inference import deps as deps_mod

    monkeypatch.setattr(
        deps_mod,
        "_EXTENSION_LOADERS",
        [
            (".ensemble", FakeForecaster),
            (".patchtst", FakeForecaster),
            (".lgbm", FakeForecaster),
        ],
    )
    reg = ModelRegistry(model_dir)
    reg.get("xmeas_1")
    assert loaded == [".ensemble"]


def test_get_falls_through_to_lgbm_when_only_kind(monkeypatch, model_dir: Path) -> None:
    _touch(model_dir / "xmeas_1.lgbm")

    loaded = []

    class FakeForecaster:
        @classmethod
        def load(cls, path: Path):
            loaded.append(path.suffix)
            return cls()

    from noether_svc_inference import deps as deps_mod

    monkeypatch.setattr(
        deps_mod,
        "_EXTENSION_LOADERS",
        [
            (".ensemble", FakeForecaster),
            (".patchtst", FakeForecaster),
            (".lgbm", FakeForecaster),
        ],
    )
    reg = ModelRegistry(model_dir)
    reg.get("xmeas_1")
    assert loaded == [".lgbm"]


def test_case_insensitive_tag_lookup(monkeypatch, model_dir: Path) -> None:
    _touch(model_dir / "xmeas_1.lgbm")

    class FakeForecaster:
        @classmethod
        def load(cls, path: Path):
            return cls()

    from noether_svc_inference import deps as deps_mod

    monkeypatch.setattr(
        deps_mod,
        "_EXTENSION_LOADERS",
        [(".lgbm", FakeForecaster)],
    )
    reg = ModelRegistry(model_dir)
    a = reg.get("XMEAS_1")
    b = reg.get("xmeas_1")
    c = reg.get("Xmeas_1")
    assert a is b is c  # cache shares one entry across casings
