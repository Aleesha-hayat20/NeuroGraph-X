"""The repository imports and the declared configuration loads."""

from __future__ import annotations

import neurographx
from neurographx.config import load


def test_package_imports():
    assert neurographx.__version__


def test_data_config_loads():
    cfg = load("data.yaml")
    assert cfg["dataset"]["phenotypic_file"].endswith(".csv")
    assert len(cfg["atlases"]) == 4
    assert cfg["frozen_evaluation_set"]["size"] == 100


def test_qc_config_loads():
    cfg = load("qc_criteria.yaml")
    assert "qc_rater_1" in cfg["rater_criteria"]
