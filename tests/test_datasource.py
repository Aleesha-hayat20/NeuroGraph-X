"""Fixture mode (memo 0014): one setting, NGX_DATA, moves every read to the fixture dataset."""

from __future__ import annotations

import pytest

from neurographx import datasource
from neurographx.config import load
from neurographx.utils.paths import project_root

ROOT = project_root()


def test_default_mode_is_real_data():
    assert datasource.mode() == "real"
    assert datasource.data_root() == ROOT
    assert datasource.describe() == {"mode": "real", "root": "."}


@pytest.mark.parametrize("value", ["real", "REAL", " real ", ""])
def test_real_mode_spellings(monkeypatch, value):
    monkeypatch.setenv("NGX_DATA", value)
    assert datasource.mode() == "real"


def test_fixture_mode_moves_the_root(monkeypatch):
    monkeypatch.setenv("NGX_DATA", "fixtures")
    assert datasource.mode() == "fixtures"
    assert datasource.is_fixture_mode()
    assert datasource.data_root() == ROOT / "fixtures"
    assert datasource.describe() == {"mode": "fixtures", "root": "fixtures"}


@pytest.mark.parametrize("value", ["fixture", "test", "synthetic", "1"])
def test_unknown_mode_is_an_error_not_a_guess(monkeypatch, value):
    monkeypatch.setenv("NGX_DATA", value)
    with pytest.raises(ValueError, match="NGX_DATA"):
        datasource.mode()


def test_real_paths_are_the_paths_the_scripts_use():
    """In real mode nothing moves: the same files scripts 05 to 07 and train_gnn.py use."""
    cfg = load("data.yaml")
    assert datasource.phenotypic_table() == \
        ROOT / cfg["paths"]["raw"] / cfg["dataset"]["phenotypic_file"]
    assert datasource.qc_cohort() == ROOT / "data/splits/qc_cohort.csv"
    assert datasource.exclusion_log() == ROOT / "docs/reports/exclusion_log.csv"
    assert datasource.frozen_set() == ROOT / "data/frozen/frozen_eval_100.csv"
    assert datasource.cv_folds() == ROOT / "data/splits/cv5_folds.csv"
    assert datasource.connectome_dir() == ROOT / "data/processed/connectomes"
    assert datasource.run_log() == ROOT / "runs/run_log.jsonl"
    assert datasource.model_registry() == ROOT / "runs/model_registry.json"
    assert datasource.analysis_log() == ROOT / "runs/analysis_log.jsonl"


def test_fixture_paths_mirror_the_real_layout(monkeypatch):
    monkeypatch.setenv("NGX_DATA", "fixtures")
    fx = ROOT / "fixtures"
    assert datasource.phenotypic_table() == fx / "data/raw/Phenotypic_V1_0b_preprocessed1.csv"
    assert datasource.qc_cohort() == fx / "data/splits/qc_cohort.csv"
    assert datasource.frozen_set() == fx / "data/frozen/frozen_eval_6.csv"
    assert datasource.run_log() == fx / "runs/run_log.jsonl"
    for path in (datasource.phenotypic_table(), datasource.qc_cohort(),
                 datasource.exclusion_log(), datasource.frozen_set(),
                 datasource.frozen_meta(), datasource.cv_folds(), datasource.run_log(),
                 datasource.model_registry()):
        assert path.exists(), path


def test_checkpoint_paths_resolve_against_the_data_root(monkeypatch):
    assert datasource.checkpoint("checkpoints/cc200_x.pt") == ROOT / "checkpoints/cc200_x.pt"
    monkeypatch.setenv("NGX_DATA", "fixtures")
    assert datasource.checkpoint("checkpoints/cc200_x.pt") == \
        ROOT / "fixtures/checkpoints/cc200_x.pt"
    absolute = ROOT / "elsewhere.pt"
    assert datasource.checkpoint(absolute) == absolute


def test_quality_rules_are_never_taken_from_the_fixture(monkeypatch):
    """The fixture exercises the real QC rules; it carries no copy of them."""
    monkeypatch.setenv("NGX_DATA", "fixtures")
    assert not (ROOT / "fixtures/configs/qc_criteria.yaml").exists()


def test_health_reports_real_mode_by_default():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from neurographx.api.main import app

    assert TestClient(app).get("/health").json()["data_mode"] == "real"
