"""Path helpers so every script resolves files the same way."""

from __future__ import annotations

from pathlib import Path

_MARKERS = ("pyproject.toml", ".git")


def project_root(start: Path | None = None) -> Path:
    """Walk upward from `start` until a repository marker is found."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if any((candidate / m).exists() for m in _MARKERS):
            return candidate
    raise RuntimeError("Could not locate the project root. Run from inside the repository.")


def resolve(relative: str, root: Path | None = None) -> Path:
    """Turn a repository-relative path from the config into an absolute path."""
    return (root or project_root()) / relative
