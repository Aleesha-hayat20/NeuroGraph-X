"""Where the service reads its data from: the real dataset or the fixture dataset.

One setting decides it, the environment variable ``NGX_DATA`` (decision memo 0014):

    NGX_DATA unset or "real"   the real ABIDE data under the repository root
    NGX_DATA="fixtures"        the small synthetic dataset committed under fixtures/

Both trees have the same layout, so every path below is "the same relative path,
under a different root":

    <root>/configs/data.yaml                      (fixtures only; real mode uses configs/)
    <root>/data/raw/<phenotypic file>             participant table
    <root>/data/splits/qc_cohort.csv              QC cohort
    <root>/docs/reports/exclusion_log.csv         exclusion log
    <root>/data/frozen/frozen_eval_<n>.csv        frozen evaluation set (+ .meta.json)
    <root>/data/splits/cv5_folds.csv              development folds
    <root>/data/processed/connectomes/<pipeline>_<strategy>/<atlas key>.npz (+ .json)
    <root>/runs/run_log.jsonl                     training run log
    <root>/runs/model_registry.json               model registry
    <root>/runs/analysis_log.jsonl                analysis log (memo 0013)
    <root>/checkpoints/<atlas>_<run_id>.pt        checkpoints, as named in the registry

Only the *reading* side (the API, later the dashboard and the integrity check) goes
through this module. The numbered pipeline scripts and the training script always
work on the real data, so pointing the service at fixtures can never overwrite
real outputs. Quality-control rules (configs/qc_criteria.yaml) are always the real
ones: the fixture exists to exercise the real rules, not a copy of them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from neurographx.config import load
from neurographx.utils.paths import project_root

ENV_VAR = "NGX_DATA"
MODES = ("real", "fixtures")
FIXTURE_DIR = "fixtures"

# Fixed locations under the data root, the same in both modes. They mirror the
# relative paths the run logger and the training script use (runs/, checkpoints/).
RUN_LOG = Path("runs/run_log.jsonl")
MODEL_REGISTRY = Path("runs/model_registry.json")
ANALYSIS_LOG = Path("runs/analysis_log.jsonl")


def mode() -> str:
    """The active data mode, from NGX_DATA. An unknown value is an error, never a guess."""
    value = os.environ.get(ENV_VAR, "").strip().lower() or "real"
    if value not in MODES:
        raise ValueError(
            f"{ENV_VAR}={os.environ.get(ENV_VAR)!r} is not a data mode. "
            f"Use one of: {', '.join(MODES)} (or leave it unset for real data)."
        )
    return value


def is_fixture_mode() -> bool:
    return mode() == "fixtures"


def data_root(which: str | None = None) -> Path:
    """Root folder of the active dataset: the repository, or the repository's fixtures/."""
    which = which or mode()
    if which not in MODES:
        raise ValueError(f"Unknown data mode {which!r}; use one of {MODES}")
    root = project_root()
    return root / FIXTURE_DIR if which == "fixtures" else root


def data_config(root: Path | None = None) -> dict[str, Any]:
    """configs/data.yaml of the active dataset (the fixture keeps its own copy)."""
    return load("data.yaml", root or data_root())


def _under(relative: str | Path, root: Path | None) -> Path:
    return (root or data_root()) / relative


# ---------------------------------------------------------------------------
# Files the service reads
# ---------------------------------------------------------------------------

def phenotypic_table(root: Path | None = None) -> Path:
    cfg = data_config(root)
    return _under(cfg["paths"]["raw"], root) / cfg["dataset"]["phenotypic_file"]


def qc_cohort(root: Path | None = None) -> Path:
    return _under(data_config(root)["cohort"]["file"], root)


def exclusion_log(root: Path | None = None) -> Path:
    return _under(data_config(root)["cohort"]["exclusion_log"], root)


def frozen_set(root: Path | None = None) -> Path:
    return _under(data_config(root)["frozen_evaluation_set"]["file"], root)


def frozen_meta(root: Path | None = None) -> Path:
    return _under(data_config(root)["frozen_evaluation_set"]["meta"], root)


def cv_folds(root: Path | None = None) -> Path:
    return _under(data_config(root)["development_splits"]["file"], root)


def connectome_dir(root: Path | None = None) -> Path:
    """The folder the engine's atlas_paths() expects (it adds <pipeline>_<strategy>/)."""
    return _under(data_config(root)["connectome"]["output_dir"], root)


def run_log(root: Path | None = None) -> Path:
    return _under(RUN_LOG, root)


def model_registry(root: Path | None = None) -> Path:
    return _under(MODEL_REGISTRY, root)


def analysis_log(root: Path | None = None) -> Path:
    return _under(ANALYSIS_LOG, root)


def checkpoint(path: str | Path, root: Path | None = None) -> Path:
    """A checkpoint path from the run log or registry, resolved against the data root.

    Registry paths are relative ("checkpoints/cc200_00252f2b.pt"), so they mean the
    same thing on every machine. An absolute path is returned unchanged.
    """
    path = Path(path)
    return path if path.is_absolute() else _under(path, root)


def describe() -> dict[str, str]:
    """What /health reports: the mode and the root, relative to the repository."""
    which = mode()
    root = data_root(which)
    try:
        shown = str(root.relative_to(project_root())) or "."
    except ValueError:  # pragma: no cover - only if the root is moved outside the repo
        shown = str(root)
    return {"mode": which, "root": shown}
