from __future__ import annotations

from neurographx.utils.paths import project_root, resolve


def test_project_root_has_pyproject():
    assert (project_root() / "pyproject.toml").exists()


def test_resolve_is_absolute():
    assert resolve("data/raw").is_absolute()
