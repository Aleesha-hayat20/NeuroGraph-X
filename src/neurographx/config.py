"""Load the declared analysis configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from neurographx.utils.paths import project_root


def load(name: str = "data.yaml", root: Path | None = None) -> dict[str, Any]:
    """Read a YAML config from configs/."""
    path = (root or project_root()) / "configs" / name
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)
