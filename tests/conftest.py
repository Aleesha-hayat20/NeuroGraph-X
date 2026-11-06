"""Shared test fixtures.

Everything built here is SYNTHETIC and carries no real participant data. Column names
mirror the real ABIDE Preprocessed file so that the code paths under test are the real ones.

API tests (memo 0013) run on the committed fixture dataset (memo 0014), copied into a
temporary folder so a test may write analyses without touching the repository.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from neurographx.utils.paths import project_root

FIXTURE_DIR = project_root() / "fixtures"
RUNTIME_FILES = ("analysis_log.jsonl", "neurographx.sqlite")

SITES = ["NYU", "UCLA_1", "KKI", "TRINITY", "SDSU", "OHSU"]


@pytest.fixture(autouse=True)
def _real_data_mode(monkeypatch):
    """Every test starts in real-data mode, whatever NGX_DATA the shell has (memo 0014).

    Tests that need the fixture dataset set NGX_DATA themselves.
    """
    monkeypatch.delenv("NGX_DATA", raising=False)


@pytest.fixture
def synthetic_phenotypic(tmp_path):
    rng = np.random.default_rng(0)
    n = 120
    df = pd.DataFrame(
        {
            "SUB_ID": np.arange(50001, 50001 + n),
            "SITE_ID": rng.choice(SITES, n),
            "DX_GROUP": rng.choice([1, 2], n),
            "SEX": rng.choice([1, 2], n, p=[0.85, 0.15]),
            "AGE_AT_SCAN": rng.uniform(6.5, 40.0, n).round(2),
            "qc_rater_1": rng.choice(["OK", "fail", "maybe"], n, p=[0.8, 0.1, 0.1]),
            "qc_anat_rater_2": rng.choice(["OK", "maybe", "fail"], n, p=[0.7, 0.2, 0.1]),
            "qc_func_rater_2": rng.choice(["OK", "maybe", "fail"], n, p=[0.7, 0.2, 0.1]),
            "qc_anat_rater_3": rng.choice(["OK", "fail"], n, p=[0.85, 0.15]),
            "qc_func_rater_3": rng.choice(["OK", "fail"], n, p=[0.85, 0.15]),
            "func_mean_fd": rng.gamma(2.0, 0.09, n).round(4),
            "func_perc_fd": rng.uniform(0, 40, n).round(2),
        }
    )
    path = tmp_path / "Phenotypic_synthetic.csv"
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Datasets and an API client for the API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_root(tmp_path) -> Path:
    """A private, writable copy of fixtures/ (without any runtime files)."""
    root = tmp_path / "fixtures"
    shutil.copytree(FIXTURE_DIR, root, ignore=shutil.ignore_patterns(*RUNTIME_FILES))
    return root


@pytest.fixture
def make_dataset(tmp_path):
    """Build a small dataset root from a phenotypic table, the way the pipeline would.

    Writes the fixture's configs/data.yaml, the phenotypic CSV, and the QC outputs made
    by m1_ingestion.qc.apply_qc with the REAL rules (completeness skipped, as there are
    no time series). No frozen set or folds unless `splits` gives them.
    """
    from neurographx.config import load
    from neurographx.m1_ingestion.qc import apply_qc

    def make(table: pd.DataFrame, name: str = "dataset",
             splits: dict[str, list[int]] | None = None) -> Path:
        root = tmp_path / name
        (root / "configs").mkdir(parents=True)
        shutil.copy(FIXTURE_DIR / "configs" / "data.yaml", root / "configs" / "data.yaml")
        cfg = load("data.yaml", root)
        raw = root / cfg["paths"]["raw"]
        raw.mkdir(parents=True)
        table.to_csv(raw / cfg["dataset"]["phenotypic_file"], index=False)
        full = table.copy()
        for column, value in (("FILE_ID", None), ("SITE_ID", "NYU"), ("DX_GROUP", 1)):
            if column not in full.columns:
                full[column] = [f"S_{s}" for s in full.SUB_ID] if value is None else value
        for column in ("qc_anat_rater_2", "qc_func_rater_2", "qc_anat_rater_3",
                       "qc_func_rater_3", "qc_rater_1"):
            if column not in full.columns:
                full[column] = "OK"
        if "func_mean_fd" not in full.columns:
            full["func_mean_fd"] = 0.1
        kept, log = apply_qc(full, load("qc_criteria.yaml"), None, [])
        cohort_path = root / cfg["cohort"]["file"]
        log_path = root / cfg["cohort"]["exclusion_log"]
        cohort_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        kept.to_csv(cohort_path, index=False)
        log.to_csv(log_path, index=False)
        if splits:
            cols = ["SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP"]
            frozen = full[full.SUB_ID.isin(splits.get("frozen", []))][cols]
            folds = full[full.SUB_ID.isin(splits.get("development", []))][cols].assign(fold=0)
            (root / cfg["frozen_evaluation_set"]["file"]).parent.mkdir(parents=True,
                                                                      exist_ok=True)
            frozen.to_csv(root / cfg["frozen_evaluation_set"]["file"], index=False)
            folds.to_csv(root / cfg["development_splits"]["file"], index=False)
        return root

    return make


@pytest.fixture
def client_for():
    """TestClient for the API reading the dataset at `root` (any folder with the layout)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from neurographx.api.main import app, get_root

    def make(root: Path, raise_server_exceptions: bool = True):
        app.dependency_overrides[get_root] = lambda: root
        return TestClient(app, raise_server_exceptions=raise_server_exceptions)

    yield make
    app.dependency_overrides.clear()


@pytest.fixture
def api(client_for, fixture_root):
    """TestClient on a private copy of the fixture dataset."""
    return client_for(fixture_root)
