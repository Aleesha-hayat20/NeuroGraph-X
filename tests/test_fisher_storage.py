"""Fisher transform and upper-triangle storage helpers. Synthetic arrays only."""

from __future__ import annotations

import numpy as np
import pytest

from neurographx.m2_connectome import connectivity as cx


@pytest.fixture
def corr():
    ts = np.random.default_rng(3).normal(size=(200, 7))
    return cx.correlation_matrix(ts)


def test_fisher_matches_textbook_formula(corr):
    z = cx.fisher_z(corr)
    off = ~np.eye(7, dtype=bool)
    expected = 0.5 * np.log((1 + corr[off]) / (1 - corr[off]))
    assert np.allclose(z[off], expected)


def test_fisher_diagonal_is_zero_and_finite(corr):
    z = cx.fisher_z(corr)
    assert np.all(np.diag(z) == 0)
    assert np.isfinite(z).all()


def test_fisher_is_inverted_by_tanh(corr):
    z = cx.fisher_z(corr)
    off = ~np.eye(7, dtype=bool)
    assert np.allclose(np.tanh(z[off]), corr[off])


def test_fisher_clips_perfect_correlation():
    r = np.array([[1.0, 1.0], [1.0, 1.0]])
    z = cx.fisher_z(r)
    assert np.isfinite(z).all()
    assert z[0, 1] == pytest.approx(np.arctanh(cx.DEFAULT_FISHER_CLIP))


def test_fisher_keeps_nan_from_flat_region():
    ts = np.random.default_rng(4).normal(size=(100, 4))
    ts[:, 2] = 1.0
    z = cx.fisher_z(cx.correlation_matrix(ts))
    assert np.isnan(z[2, [0, 1, 3]]).all() and np.isnan(z[[0, 1, 3], 2]).all()
    assert np.isfinite(np.delete(np.delete(z, 2, 0), 2, 1)).all()


def test_fisher_rejects_bad_clip(corr):
    with pytest.raises(ValueError):
        cx.fisher_z(corr, clip=1.0)


def test_triu_roundtrip(corr):
    vec = cx.to_triu(corr)
    assert vec.shape == (7 * 6 // 2,)
    back = cx.from_triu(vec, 7, diagonal=1.0)
    assert np.allclose(back, corr)


def test_triu_order_is_row_major():
    m = np.arange(16.0).reshape(4, 4)
    m = (m + m.T) / 2
    assert list(cx.to_triu(m)) == [m[0, 1], m[0, 2], m[0, 3], m[1, 2], m[1, 3], m[2, 3]]


def test_from_triu_rejects_wrong_length():
    with pytest.raises(ValueError):
        cx.from_triu(np.zeros(5), 4, diagonal=0.0)


@pytest.mark.parametrize("n", [2, 111, 116, 161, 200])
def test_regions_from_edges(n):
    assert cx.n_regions_from_edges(n * (n - 1) // 2) == n
