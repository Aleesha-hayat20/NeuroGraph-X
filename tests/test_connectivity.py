"""Connectivity matrix construction and its checks.

All arrays here are synthetic and exist only to exercise the code paths.
"""

from __future__ import annotations

import numpy as np
import pytest

from neurographx.m2_connectome import connectivity as cx


@pytest.fixture
def ts():
    return np.random.default_rng(0).normal(size=(150, 6))


def test_shape_is_regions_by_regions(ts):
    corr = cx.correlation_matrix(ts)
    assert corr.shape == (6, 6)


def test_wrong_orientation_is_detectable(ts):
    wrong = np.corrcoef(ts)            # numpy default, rows treated as variables
    assert wrong.shape == (150, 150)   # square, plausible, and wrong
    assert cx.correlation_matrix(ts).shape != wrong.shape


def test_clean_matrix_is_valid(ts):
    corr = cx.correlation_matrix(ts)
    report = cx.check_matrix(corr, cx.zero_variance_regions(ts))
    assert report["nan_cells"] == 0
    assert report["symmetric"] and report["diagonal_ones"]
    assert cx.is_valid(report)


def test_zero_variance_region_is_found(ts):
    ts[:, 3] = 2.5
    assert list(cx.zero_variance_regions(ts)) == [3]


def test_zero_variance_nan_is_explained_and_still_valid(ts):
    ts[:, 3] = 2.5
    zv = cx.zero_variance_regions(ts)
    corr = cx.correlation_matrix(ts)
    report = cx.check_matrix(corr, zv)
    assert report["nan_cells"] == 6 * 6 - 5 * 5
    assert report["nan_explained_by_zero_variance"] is True
    assert report["diagonal_ones"]          # NaN diagonal entry is excluded
    assert cx.is_valid(report)


def test_rejects_1d_input():
    with pytest.raises(ValueError):
        cx.correlation_matrix(np.arange(10.0))


def test_load_1d_skips_header(tmp_path):
    p = tmp_path / "x_rois_cc200.1D"
    p.write_text("#roi_1\troi_2\troi_3\n1 2 3\n2 4 1\n3 1 2\n")
    arr = cx.load_1d(p)
    assert arr.shape == (3, 3)
