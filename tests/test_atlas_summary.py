"""Atlas summary logic. Arrays here are synthetic."""

from __future__ import annotations

import numpy as np

from neurographx.m1_ingestion.atlas_summary import render, summarise_atlas


def _arrays(n=4, t=120, r=8, zero_var_in=None):
    rng = np.random.default_rng(1)
    out = []
    for i in range(n):
        a = rng.normal(size=(t + i * 10, r))
        if zero_var_in is not None and i == zero_var_in:
            a[:, 2] = 0.0
        out.append(a)
    return out


def test_counts_regions_and_timepoints(tmp_path):
    row = summarise_atlas("rois_x", "X", "test", _arrays(), ["a", "b", "c", "d"], tmp_path)
    assert row["regions"] == 8 and row["regions_consistent"]
    assert row["timepoints_min"] == 120 and row["timepoints_max"] == 150
    assert row["invalid_matrices"] == 0


def test_zero_variance_counted_but_still_valid(tmp_path):
    row = summarise_atlas("rois_x", "X", "test", _arrays(zero_var_in=1),
                          ["a", "b", "c", "d"], tmp_path)
    assert row["participants_with_zero_variance"] == 1
    assert row["invalid_matrices"] == 0


def test_inconsistent_region_counts_flagged(tmp_path):
    arrays = _arrays()
    arrays[2] = arrays[2][:, :7]
    row = summarise_atlas("rois_x", "X", "test", arrays, ["a", "b", "c", "d"], tmp_path)
    assert not row["regions_consistent"]


def test_render_reports_same_participant_set(tmp_path):
    ids = ["a", "b", "c", "d"]
    rows = [summarise_atlas(k, k, "f", _arrays(), ids, tmp_path) for k in ("r1", "r2")]
    text = render(rows, {"date": "2026-10-01", "pipeline": "cpac",
                         "strategy": "filt_global", "nilearn": "0.14.1"})
    assert "Same participant set across all four atlases: **yes**" in text
    assert "| r1 |" in text
