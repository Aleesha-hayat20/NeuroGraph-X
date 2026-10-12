"""Tests for the ABIDE graph loader (m3_model.data). SYNTHETIC connectomes only.

Skipped where PyTorch or PyTorch Geometric is not installed.
"""
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx.m2_connectome import connectivity as cx  # noqa: E402
from neurographx.m2_connectome.engine import ConnectomeSet  # noqa: E402
from neurographx.m3_model.data import (  # noqa: E402
    build_graphs,
    flat_region_summary,
    labels_from_dx,
    make_get_graph,
    short_atlas_name,
)

R = 12


@pytest.fixture
def cset():
    rng = np.random.default_rng(0)
    z_rows, zero_var = [], []
    for i in range(4):
        z = rng.normal(0, 0.3, (R, R))
        z = (z + z.T) / 2
        np.fill_diagonal(z, 0)
        zv = np.zeros(R, bool)
        if i == 1:  # participant 1 has a flat region 5: NaN row and column on disk
            z[5, :] = np.nan
            z[:, 5] = np.nan
            zv[5] = True
        z_rows.append(cx.to_triu(z))
        zero_var.append(zv)
    z_triu = np.array(z_rows, np.float32)
    return ConnectomeSet(
        atlas_key="rois_test", n_regions=R,
        file_ids=np.array(["A_0050001", "A_0050002", "B_0050003", "B_0050004"]),
        sub_ids=np.array([50001, 50002, 50003, 50004]),
        r_triu=np.tanh(z_triu), z_triu=z_triu, zero_var=np.array(zero_var),
        n_timepoints=np.full(4, 100),
    )


@pytest.fixture
def table():
    return pd.DataFrame({"SUB_ID": [50001, 50002, 50003, 50004],
                         "FILE_ID": ["A_0050001", "A_0050002", "B_0050003", "B_0050004"],
                         "SITE_ID": ["A", "A", "B", "B"], "DX_GROUP": [1, 2, 1, 2]})


def test_label_coding_autism_is_1_control_is_0():
    assert labels_from_dx(pd.Series([1, 2, 2, 1])).tolist() == [1, 0, 0, 1]
    with pytest.raises(ValueError):
        labels_from_dx(pd.Series([1, 3]))


def test_graphs_have_atlas_size_labels_and_sites(cset, table):
    graphs = build_graphs(cset, table, density=0.2)
    assert [int(g.y) for g in graphs] == [1, 0, 1, 0]
    assert all(g.x.shape == (R, R) for g in graphs)
    assert [g.site for g in graphs] == ["A", "A", "B", "B"]
    assert graphs[0].atlas == "test"


def test_flat_region_is_filled_and_counted(cset, table):
    g = build_graphs(cset, table, fill_nan=0.0)[1]
    assert not g.x.isnan().any()
    assert g.x[5].abs().sum() == 0 and g.n_flat_regions == 1


def test_unfilled_nan_still_fails_loudly(cset, table):
    with pytest.raises(ValueError, match="NaN"):
        build_graphs(cset, table.iloc[[1]], fill_nan=np.nan)


def test_get_graph_accepts_api_ids_and_rejects_unknown(cset):
    get_graph = make_get_graph(cset, density=0.2)
    assert get_graph("0050003").x.shape == (R, R)
    with pytest.raises(KeyError):
        get_graph("0099999")


def test_flat_region_summary_by_group(cset, table):
    s = flat_region_summary(cset, table)
    assert s["control"]["with_flat_regions"] == 1 and s["autism"]["with_flat_regions"] == 0


def test_short_atlas_name():
    assert short_atlas_name("rois_cc200") == "cc200"
