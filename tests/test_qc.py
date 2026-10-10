"""Quality control gates on the synthetic phenotypic frame."""

from __future__ import annotations

import pandas as pd
import pytest

from neurographx.config import load
from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion.qc import apply_qc, gate_counts
from neurographx.utils.paths import resolve


@pytest.fixture
def frame(synthetic_phenotypic):
    df = md.load_phenotypic(synthetic_phenotypic)
    df["FILE_ID"] = [f"{s}_{i:07d}" for s, i in zip(df.SITE_ID, df.SUB_ID)]
    return df


def test_qc_config_is_closed():
    qc = load("qc_criteria.yaml")
    assert qc["motion"]["column"] == "func_mean_fd"
    assert qc["motion"]["mean_fd_max"] == 0.5


def test_retained_and_excluded_partition_the_input(frame):
    qc = load("qc_criteria.yaml")
    kept, log = apply_qc(frame, qc, None, [])
    assert len(kept) + len(log) == len(frame)
    assert set(kept.SUB_ID).isdisjoint(log.SUB_ID)
    c = gate_counts(log, len(frame))
    assert c["retained"] == len(kept)


def test_every_exclusion_has_a_reason(frame):
    kept, log = apply_qc(frame, load("qc_criteria.yaml"), None, [])
    assert (log["reasons"].str.len() > 0).all()
    assert set(log["first_gate_failed"]) <= {"rater", "motion", "completeness"}


def test_motion_gate(frame):
    qc = load("qc_criteria.yaml")
    for c in qc["rater_criteria"]:
        frame[c] = "OK"
    frame.loc[0, "func_mean_fd"] = 0.51
    frame.loc[1, "func_mean_fd"] = 0.50          # exactly at the threshold is kept
    frame.loc[2, "func_mean_fd"] = None          # missing motion fails the gate
    kept, log = apply_qc(frame, qc, None, [])
    excluded = set(log.SUB_ID)
    assert frame.SUB_ID[0] in excluded and frame.SUB_ID[2] in excluded
    assert frame.SUB_ID[1] in set(kept.SUB_ID)
    assert (log.first_gate_failed == "motion").all()


def test_completeness_gate(frame, tmp_path):
    qc = load("qc_criteria.yaml")
    for c in qc["rater_criteria"]:
        frame[c] = "OK"
    frame["func_mean_fd"] = 0.1
    small = frame.head(3).copy()
    good, empty = small.FILE_ID.iloc[0], small.FILE_ID.iloc[1]
    (tmp_path / f"{good}_rois_x.1D").write_text("#1 #2\n1 2\n3 4\n")
    (tmp_path / f"{empty}_rois_x.1D").write_text("#1 #2\n")
    kept, log = apply_qc(small, qc, tmp_path, ["rois_x"])
    assert list(kept.FILE_ID) == [good]
    reasons = dict(zip(log.FILE_ID, log.reasons))
    assert "empty" in reasons[empty]
    assert "missing" in reasons[small.FILE_ID.iloc[2]]


def test_missing_rater_column_is_an_error(frame):
    with pytest.raises(KeyError):
        apply_qc(frame.drop(columns=["qc_rater_1"]), load("qc_criteria.yaml"), None, [])


def test_committed_cohort_matches_memo():
    cohort = pd.read_csv(resolve(load("data.yaml")["cohort"]["file"]))
    assert len(cohort) == 861
    assert not cohort.SUB_ID.duplicated().any()
    assert (cohort.mean_fd <= 0.5).all()
