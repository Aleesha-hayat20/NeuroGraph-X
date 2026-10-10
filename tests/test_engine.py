"""Connectome engine: build, storage, reload, caching. Synthetic .1D files only."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from neurographx.m2_connectome import connectivity as cx
from neurographx.m2_connectome import engine as eg

KEY = "rois_test"


def _write_1d(path, ts):
    header = "\t".join(f"#{i + 1}" for i in range(ts.shape[1]))
    body = "\n".join("\t".join(f"{v:.6f}" for v in row) for row in ts)
    path.write_text(header + "\n" + body + "\n")


@pytest.fixture
def setup(tmp_path):
    rng = np.random.default_rng(11)
    ts_dir = tmp_path / "ts"
    ts_dir.mkdir()
    ids = ["SITEA_0050001", "SITEA_0050002", "SITEB_0050003"]
    for k, fid in enumerate(ids):
        ts = rng.normal(size=(80 + 10 * k, 6))
        if k == 1:
            ts[:, 4] = 0.0                      # a flat region in one participant
        _write_1d(ts_dir / f"{fid}_{KEY}.1D", ts)
    cohort = pd.DataFrame({"FILE_ID": ids, "SUB_ID": [50001, 50002, 50003]})
    return cohort, ts_dir, tmp_path / "out"


def _build(setup, **kw):
    cohort, ts_dir, out = setup
    return eg.build_atlas(KEY, cohort, ts_dir, out, "cpac", "filt_global", **kw)


def test_build_shapes_and_manifest(setup):
    cset, status = _build(setup)
    assert status == "built"
    assert len(cset) == 3 and cset.n_regions == 6 and cset.n_edges == 15
    assert cset.r_triu.dtype == np.float32 and cset.z_triu.shape == (3, 15)
    assert cset.zero_var.sum() == 1 and cset.zero_var[1, 4]
    assert list(cset.n_timepoints) == [80, 90, 100]
    m = cset.manifest
    assert m["n_regions"] == 6 and m["engine_version"] == eg.ENGINE_VERSION
    assert m["participants_with_zero_variance"] == 1


def test_stored_matrix_equals_direct_computation(setup):
    cohort, ts_dir, _ = setup
    cset, _ = _build(setup)
    ts = cx.load_1d(ts_dir / f"{cohort.FILE_ID[0]}_{KEY}.1D")
    r = cx.correlation_matrix(ts)
    assert np.allclose(cset.matrix(cohort.FILE_ID[0], "r"), r, atol=1e-6)
    assert np.allclose(cset.matrix(50001, "z"), cx.fisher_z(r), atol=1e-5)


def test_matrix_conventions_for_flat_region(setup):
    cset, _ = _build(setup)
    r = cset.matrix("SITEA_0050002", "r")
    z = cset.matrix("SITEA_0050002", "z")
    assert np.isnan(r[4]).all() and np.isnan(r[:, 4]).all()
    assert np.diag(r)[[0, 1, 2, 3, 5]].tolist() == [1, 1, 1, 1, 1]
    assert np.all(np.diag(z) == 0)
    filled = cset.matrix("SITEA_0050002", "z", fill_nan=0.0)
    assert np.isfinite(filled).all() and filled[4, 0] == 0


def test_stack_and_subset_order(setup):
    cset, _ = _build(setup)
    full = cset.stack("z", fill_nan=0.0)
    assert full.shape == (3, 6, 6)
    sub = cset.stack("z", fill_nan=0.0, participants=[50003, 50001])
    assert np.array_equal(sub[0], full[2]) and np.array_equal(sub[1], full[0])


def test_unknown_participant_raises(setup):
    cset, _ = _build(setup)
    with pytest.raises(KeyError):
        cset.matrix("NOPE_0000000")


def test_second_run_uses_cache(setup, monkeypatch):
    _build(setup)
    calls = []
    monkeypatch.setattr(eg, "compute_subject", lambda *a, **k: calls.append(1))
    cset, status = _build(setup)
    assert status == "cached" and not calls and len(cset) == 3


def test_changed_input_invalidates_cache(setup):
    cohort, ts_dir, _ = setup
    first, _ = _build(setup)
    path = ts_dir / f"{cohort.FILE_ID[2]}_{KEY}.1D"
    _write_1d(path, np.random.default_rng(99).normal(size=(100, 6)))
    second, status = _build(setup)
    assert status == "built"
    assert not np.allclose(first.r_triu[2], second.r_triu[2])


def test_changed_parameter_invalidates_cache(setup):
    _build(setup)
    _, status = _build(setup, clip=0.999)
    assert status == "built"


def test_force_rebuilds(setup):
    _build(setup)
    _, status = _build(setup, force=True)
    assert status == "built"


def test_tampered_store_is_rebuilt(setup):
    cohort, ts_dir, out = setup
    _build(setup)
    npz, manifest = eg.atlas_paths(out, "cpac", "filt_global", KEY)
    with npz.open("ab") as fh:
        fh.write(b"tamper")
    eg._MEMO.clear()
    with pytest.raises(ValueError):
        eg.load_atlas(npz, manifest)
    _, status = _build(setup)
    assert status == "built"
    assert json.loads(manifest.read_text())["output_sha256"] == eg.sha256_file(npz)


def test_missing_file_is_reported(setup):
    cohort, ts_dir, out = setup
    extra = pd.concat([cohort, pd.DataFrame({"FILE_ID": ["X_1"], "SUB_ID": [1]})])
    with pytest.raises(FileNotFoundError):
        eg.build_atlas(KEY, extra, ts_dir, out, "cpac", "filt_global")


def test_duplicate_participant_rejected(setup):
    cohort, ts_dir, out = setup
    with pytest.raises(ValueError):
        eg.build_atlas(KEY, pd.concat([cohort, cohort]), ts_dir, out, "cpac", "filt_global")


def test_compute_subject_rejects_single_timepoint():
    with pytest.raises(ValueError):
        eg.compute_subject(np.ones((1, 5)))


def test_unknown_kind_rejected(setup):
    cset, _ = _build(setup)
    with pytest.raises(ValueError):
        cset.edges("pearson")
