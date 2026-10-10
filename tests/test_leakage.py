"""LEAKAGE ASSERTION (deliverable A8).

Fails the build if any participant in the frozen evaluation set appears in a
training split. It checks three things:

1. Every split file committed under data/splits/ (except the QC cohort itself).
   Any file Laiba or anyone else adds there is picked up automatically.
2. The development pool: QC cohort minus frozen set has no overlap and nothing lost.
3. The guard itself: a deliberately leaking split must be caught, matching on
   SUB_ID or FILE_ID, so a silently broken check cannot pass.

Training code must also call `assert_no_leakage(train_ids, frozen)` before fitting.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from neurographx.config import load
from neurographx.m1_ingestion import splits as sp
from neurographx.utils.paths import resolve

CFG = load("data.yaml")
FROZEN_PATH = resolve(CFG["frozen_evaluation_set"]["file"])
COHORT_PATH = resolve(CFG["cohort"]["file"])
SPLITS_DIR = resolve(CFG["paths"]["splits"])


def _split_files() -> list[Path]:
    return sorted(p for p in SPLITS_DIR.glob("*.csv") if p.resolve() != COHORT_PATH.resolve())


@pytest.fixture(scope="module")
def frozen() -> pd.DataFrame:
    assert FROZEN_PATH.exists(), "The frozen evaluation set must be committed"
    return sp.read_ids(FROZEN_PATH)


def test_at_least_one_training_split_is_committed():
    assert _split_files(), f"No split files under {SPLITS_DIR}, nothing would be checked"


@pytest.mark.parametrize("path", _split_files(), ids=lambda p: p.name)
def test_no_frozen_participant_in_any_training_split(path, frozen):
    split = sp.read_ids(path)
    sp.assert_no_leakage(sp.training_rows(split), frozen, context=path.name)


def test_development_pool_is_cohort_minus_frozen(frozen):
    cohort = pd.read_csv(COHORT_PATH)
    folds = pd.read_csv(resolve(CFG["development_splits"]["file"]))
    assert set(folds.SUB_ID).isdisjoint(frozen.SUB_ID)
    assert set(folds.SUB_ID) | set(frozen.SUB_ID) == set(cohort.SUB_ID)
    assert len(folds) + len(frozen) == len(cohort)


# --- the guard must actually fire --------------------------------------------

def test_guard_catches_a_leak_by_sub_id(frozen):
    leaking = pd.DataFrame({"SUB_ID": [1, 2, int(frozen.SUB_ID.iloc[0])]})
    with pytest.raises(sp.LeakageError, match="1 frozen"):
        sp.assert_no_leakage(leaking, frozen)


def test_guard_catches_a_leak_by_file_id_alone(frozen):
    leaking = pd.DataFrame({"SUB_ID": [-1], "FILE_ID": [frozen.FILE_ID.iloc[5]]})
    with pytest.raises(sp.LeakageError):
        sp.assert_no_leakage(leaking, frozen)


def test_guard_accepts_plain_id_lists(frozen):
    sp.assert_no_leakage([1, 2, 3], frozen)
    with pytest.raises(sp.LeakageError):
        sp.assert_no_leakage(list(frozen.SUB_ID[:3]), frozen)


def test_guard_catches_a_leaking_split_file(frozen, tmp_path):
    folds = pd.read_csv(resolve(CFG["development_splits"]["file"]))
    bad = pd.concat([folds, frozen.assign(fold=0)])
    path = tmp_path / "bad_split.csv"
    bad.to_csv(path, index=False)
    with pytest.raises(sp.LeakageError, match="100 frozen"):
        sp.assert_no_leakage(sp.training_rows(sp.read_ids(path)), frozen)


def test_role_column_only_test_rows_may_hold_frozen_ids(frozen):
    split = pd.DataFrame({"SUB_ID": [int(frozen.SUB_ID.iloc[0]), 7],
                          "role": ["test", "train"]})
    sp.assert_no_leakage(sp.training_rows(split), frozen)
    with pytest.raises(sp.LeakageError):
        sp.assert_no_leakage(sp.training_rows(split.assign(role="train")), frozen)
