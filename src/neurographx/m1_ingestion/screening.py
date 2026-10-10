"""Per-participant quality screen (decision memo 0003), with a reason for every exclusion.

Rules come from configs/qc_criteria.yaml, never from code. What is applied today:

- Gate 1, rater criteria: applied, to every rater column the file has.
- Gate 2, head motion: applied when a motion rule is passed (memo 0003, closed 6 October:
  func_mean_fd at most 0.5 mm; a missing value fails). The API passes it.
- Gate 3, part one: a FILE_ID of "no_filename" means ABIDE has no preprocessed data for
  that participant, so the participant is excluded.

Gates 1 and 3 (part one) are exactly the screen nilearn.datasets.fetch_abide_pcp(
quality_checked=True) applies (nilearn 0.14.1), which gave the 871 participants the atlases
were downloaded for. Adding gate 2 gives the 861 of data/splits/qc_cohort.csv, the cohort
written by scripts/05_apply_qc.py (m1_ingestion/qc.py). A test checks the two agree.

Not applied here: the rest of gate 3 (time series files present and non-empty), which needs
the downloaded data. qc.py applies it; it excluded nobody in the Week 2 run.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from neurographx.config import load

NO_FILE = "no_filename"


def rater_criteria(root: Path | None = None) -> dict[str, list[str]]:
    """Accepted values per rater column, from configs/qc_criteria.yaml."""
    return load("qc_criteria.yaml", root)["rater_criteria"]


def motion_rule(root: Path | None = None) -> dict | None:
    """The head motion gate from configs/qc_criteria.yaml: {"column": ..., "mean_fd_max": ...}."""
    rule = load("qc_criteria.yaml", root).get("motion")
    return rule if rule and "column" in rule else None


def exclusion_reasons(row: pd.Series, criteria: dict[str, list[str]],
                      motion: dict | None = None) -> list[str]:
    """Every reason one participant fails the screen. An empty list means included."""
    reasons = []
    file_id = row.get("FILE_ID")
    if isinstance(file_id, str) and file_id.strip() == NO_FILE:
        reasons.append("no preprocessed data in ABIDE (FILE_ID is no_filename)")
    for column, accepted in criteria.items():
        if column not in row.index:
            continue  # memo 0003: a criterion applies only if its column exists
        value = row[column]
        text = "" if pd.isna(value) else str(value).strip()
        if text not in accepted:
            reasons.append(f"{column} is {text or 'missing'} (accepted: {', '.join(accepted)})")
    if motion and motion["column"] in row.index:  # like the raters: needs its column
        column, limit = motion["column"], float(motion["mean_fd_max"])
        value = pd.to_numeric(row.get(column), errors="coerce")
        if pd.isna(value):
            reasons.append(f"{column} is missing (head motion gate)")
        elif value > limit:
            reasons.append(f"{column} is {value:.3f} (accepted: at most {limit} mm)")
    return reasons
