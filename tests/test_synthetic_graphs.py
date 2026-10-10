"""Tests for the brain-shaped synthetic graph generator (m3_model).

Skipped automatically where PyTorch or PyTorch Geometric is not installed
(the CI image currently has neither); they run on Kaggle and anywhere the
model libraries are installed.
"""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx.m3_model.synthetic_brain import (  # noqa: E402
    make_dataset,
    matrix_to_graph,
)


def test_shapes_and_validity():
    for g in make_dataset(n_subjects=10, n_rois=200, seed=1):
        assert g.x.shape == (200, 200)
        assert torch.isfinite(g.x).all()
        assert (g.edge_index[0] != g.edge_index[1]).all()  # no self-loops
        assert (g.edge_weight >= 0).all()
        assert g.edge_index.shape[1] == 2 * round(0.10 * 200 * 199 / 2)


def test_edges_are_symmetric():
    g = make_dataset(n_subjects=1, seed=2)[0]
    pairs = set(map(tuple, g.edge_index.t().tolist()))
    assert all((j, i) in pairs for (i, j) in pairs)


def test_other_node_count_aal_sized():
    g = make_dataset(n_subjects=2, n_rois=116, seed=3)[0]
    assert g.num_nodes == 116 and g.x.shape == (116, 116)


def test_rejects_nan_matrix():
    z = np.zeros((5, 5), dtype=np.float32)
    z[0, 1] = z[1, 0] = np.nan
    with pytest.raises(ValueError):
        matrix_to_graph(z, label=0)


def test_same_seed_same_data():
    a = make_dataset(n_subjects=3, seed=4)
    b = make_dataset(n_subjects=3, seed=4)
    assert all(torch.equal(g1.x, g2.x) for g1, g2 in zip(a, b))
