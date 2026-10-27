"""Shared test fixtures.

The phenotypic frame built here is SYNTHETIC. It exists only to exercise the
report code and carries no real participant data. Column names mirror the real
ABIDE Preprocessed file so that the code paths under test are the real ones.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

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
