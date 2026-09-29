"""The metadata report builds and reports what it actually found."""

from __future__ import annotations

import pandas as pd

from neurographx.m1_ingestion import metadata as md


def test_finds_qc_and_motion_columns(synthetic_phenotypic):
    df = md.load_phenotypic(synthetic_phenotypic)
    qc = md.find_qc_columns(df)
    assert "qc_rater_1" in qc and len(qc) == 5
    motion = md.find_motion_columns(df)
    assert "func_mean_fd" in motion


def test_counts_and_bands(synthetic_phenotypic):
    df = md.load_phenotypic(synthetic_phenotypic)
    groups = md._counts(df, "DX_GROUP", md.DX_LABELS)
    assert set(groups["label"]) <= {"Autism", "Control"}
    bands = md.age_bands(df)
    assert bands["count"].sum() == len(df)


def test_site_by_group_has_total(synthetic_phenotypic):
    df = md.load_phenotypic(synthetic_phenotypic)
    table = md.site_by_group(df)
    assert "Total" in table.columns
    assert table["Total"].sum() == len(df)


def test_rater_filter_is_applicable(synthetic_phenotypic):
    df = md.load_phenotypic(synthetic_phenotypic)
    result = md.would_pass_all_raters(df)
    assert result["applicable"]
    assert 0 < result["passing_all"] <= result["total"]


def test_missing_columns_do_not_crash():
    df = pd.DataFrame({"SUB_ID": [1, 2, 3]})
    assert md._counts(df, "DX_GROUP") is None
    assert md.age_bands(df) is None
    assert md.site_by_group(df) is None
    assert md.qc_summary(df) is None
    assert md.would_pass_all_raters(df) == {"applicable": False}
