"""The frozen evaluation set: drawing logic on synthetic data, and the committed file."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from neurographx.config import load
from neurographx.m1_ingestion import splits as sp
from neurographx.utils.paths import resolve

CFG = load("data.yaml")
FZ = CFG["frozen_evaluation_set"]


# --- drawing logic, synthetic ------------------------------------------------

@pytest.fixture
def cohort():
    rng = np.random.default_rng(5)
    n = 600
    return pd.DataFrame({
        "SUB_ID": np.arange(50001, 50001 + n),
        "FILE_ID": [f"S_{i}" for i in range(n)],
        "SITE_ID": rng.choice(["A", "B", "C", "D", "E"], n, p=[0.4, 0.3, 0.15, 0.1, 0.05]),
        "DX_GROUP": rng.choice([1, 2], n),
    })


def test_allocation_sums_and_bounds():
    counts = pd.Series({"a": 7, "b": 3, "c": 1, "d": 89})
    alloc = sp.allocate(counts, 10)
    assert alloc.sum() == 10
    assert (alloc <= counts.sort_index()).all()


def test_allocation_is_proportional_within_one():
    counts = pd.Series({"a": 172, "b": 85, "c": 15, "d": 589})
    alloc = sp.allocate(counts, 100)
    exact = counts.sort_index() * 100 / counts.sum()
    assert (np.abs(alloc - exact) < 1).all()


def test_allocation_rejects_impossible_size():
    with pytest.raises(ValueError):
        sp.allocate(pd.Series({"a": 3}), 4)


def test_draw_is_reproducible_and_seed_sensitive(cohort):
    a, _ = sp.stratified_draw(cohort, 100, ["SITE_ID", "DX_GROUP"], seed=1)
    b, _ = sp.stratified_draw(cohort.sample(frac=1, random_state=0), 100,
                              ["SITE_ID", "DX_GROUP"], seed=1)
    c, _ = sp.stratified_draw(cohort, 100, ["SITE_ID", "DX_GROUP"], seed=2)
    assert list(a.SUB_ID) == list(b.SUB_ID)       # input row order does not matter
    assert list(a.SUB_ID) != list(c.SUB_ID)


def test_draw_respects_strata(cohort):
    drawn, table = sp.stratified_draw(cohort, 100, ["SITE_ID", "DX_GROUP"], seed=1)
    assert len(drawn) == 100 and not drawn.SUB_ID.duplicated().any()
    got = drawn.groupby(["SITE_ID", "DX_GROUP"]).size()
    want = table.set_index(["SITE_ID", "DX_GROUP"])["drawn"]
    assert got.reindex(want.index, fill_value=0).equals(want)


def test_write_refuses_to_overwrite(cohort, tmp_path):
    drawn, table = sp.stratified_draw(cohort, 50, ["SITE_ID", "DX_GROUP"], seed=1)
    cpath = tmp_path / "cohort.csv"
    cohort.to_csv(cpath, index=False)
    args = (tmp_path / "f.csv", tmp_path / "f.json", cpath, 1, ["SITE_ID", "DX_GROUP"])
    sp.write_frozen(drawn, table, *args)
    with pytest.raises(FileExistsError):
        sp.write_frozen(drawn, table, *args)


def test_folds_cover_pool_once(cohort):
    folds = sp.make_folds(cohort, 5, ["SITE_ID", "DX_GROUP"], seed=3)
    assert len(folds) == len(cohort) and set(folds.fold) == set(range(5))
    sizes = folds.fold.value_counts()
    assert sizes.max() - sizes.min() <= 1


# --- the committed file ------------------------------------------------------

@pytest.fixture(scope="module")
def frozen():
    return pd.read_csv(resolve(FZ["file"]))


@pytest.fixture(scope="module")
def meta():
    return json.loads(resolve(FZ["meta"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def qc_cohort():
    return pd.read_csv(resolve(CFG["cohort"]["file"]))


def test_frozen_file_is_committed_with_the_right_size(frozen):
    assert len(frozen) == FZ["size"] == 100
    assert list(frozen.columns) == sp.KEY_COLUMNS
    assert not frozen.SUB_ID.duplicated().any() and not frozen.FILE_ID.duplicated().any()


def test_frozen_file_has_not_been_edited(meta):
    assert sp.sha256_text(resolve(FZ["file"])) == meta["frozen_sha256"], (
        "frozen_eval_100.csv differs from the hash recorded when it was drawn. "
        "The frozen set must never be edited or regenerated."
    )


def test_seed_is_recorded_and_matches_config(meta):
    assert meta["seed"] == FZ["seed"]
    assert meta["stratify_by"] == FZ["stratify_by"] == ["SITE_ID", "DX_GROUP"]


def test_frozen_participants_all_passed_qc(frozen, qc_cohort):
    assert set(frozen.SUB_ID) <= set(qc_cohort.SUB_ID)
    merged = frozen.merge(qc_cohort, on="SUB_ID", suffixes=("", "_c"))
    assert (merged.FILE_ID == merged.FILE_ID_c).all()


def test_cohort_is_the_one_the_set_was_drawn_from(meta):
    assert sp.sha256_text(resolve(CFG["cohort"]["file"])) == meta["cohort_sha256"]


def test_stratification_follows_the_recorded_allocation(frozen, meta):
    got = frozen.groupby(["SITE_ID", "DX_GROUP"]).size().to_dict()
    for row in meta["allocation"]:
        assert got.get((row["SITE_ID"], row["DX_GROUP"]), 0) == row["drawn"]


def test_every_site_and_both_groups_represented(frozen, qc_cohort):
    assert set(frozen.SITE_ID) == set(qc_cohort.SITE_ID)
    assert set(frozen.DX_GROUP) == {1, 2}


def test_draw_is_reproducible_from_the_recorded_seed(frozen, qc_cohort, meta):
    redrawn, _ = sp.stratified_draw(qc_cohort, meta["size"], meta["stratify_by"], meta["seed"])
    assert list(redrawn.SUB_ID) == list(frozen.SUB_ID), (
        "The recorded seed no longer reproduces the frozen set. If numpy changed its "
        "random generator, the COMMITTED file stays authoritative; do not redraw."
    )
