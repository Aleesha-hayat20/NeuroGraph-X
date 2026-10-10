"""The independent verifier agrees with the engine and catches a wrong matrix."""

from __future__ import annotations

import numpy as np
import pytest

from neurographx.m2_connectome import connectivity as cx
from neurographx.m2_connectome import verify as vf
from neurographx.m2_connectome.engine import compute_subject


@pytest.fixture
def case():
    ts = np.random.default_rng(21).normal(size=(150, 9))
    ts[:, 6] = 3.0
    out = compute_subject(ts)
    r = cx.from_triu(out["r_triu"], 9, 1.0)
    r[6, 6] = np.nan
    z = cx.from_triu(out["z_triu"], 9, 0.0)
    return ts, r, z, out["zero_var"]


def test_manual_pearson_matches_numpy():
    ts = np.random.default_rng(1).normal(size=(90, 5))
    assert np.allclose(vf.manual_pearson(ts), np.corrcoef(ts, rowvar=False))


def test_independent_reader(tmp_path):
    p = tmp_path / "a.1D"
    p.write_text("#1\t#2\n1.5\t2\n3\t-4\n")
    assert vf.read_1d_independent(p).tolist() == [[1.5, 2.0], [3.0, -4.0]]


def test_engine_output_passes(case):
    ts, r, z, zv = case
    res = vf.verify_one(r, z, zv, ts, cx.DEFAULT_FISHER_CLIP, np.random.default_rng(0), 20)
    assert res["passed"] and res["nan_pattern_match"] and res["flat_regions"] == 1


def test_corrupted_value_is_caught(case):
    ts, r, z, zv = case
    r = r.copy()
    r[0, 1] = r[1, 0] = r[0, 1] + 1e-3
    res = vf.verify_one(r, z, zv, ts, cx.DEFAULT_FISHER_CLIP, np.random.default_rng(0), 20)
    assert not res["passed"]


def test_wrong_fisher_is_caught(case):
    ts, r, z, zv = case
    res = vf.verify_one(r, np.tanh(z), zv, ts, cx.DEFAULT_FISHER_CLIP,
                        np.random.default_rng(0), 20)
    assert not res["passed"]


def test_wrong_nan_pattern_is_caught(case):
    ts, r, z, zv = case
    res = vf.verify_one(np.nan_to_num(r), z, zv, ts, cx.DEFAULT_FISHER_CLIP,
                        np.random.default_rng(0), 20)
    assert not res["nan_pattern_match"] and not res["passed"]
