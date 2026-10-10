"""Per-participant quality screen (decision memo 0003), with a reason for every exclusion.

Rules come from configs/qc_criteria.yaml, never from code. What is applied today:

- Gate 1, rater criteria: applied, to every rater column the file has.
- Gate 3, part one: a FILE_ID of "no_filename" means ABIDE has no preprocessed data for
  that participant, so the participant is excluded.

Together these are exactly the screen nilearn.datasets.fetch_abide_pcp(quality_checked=True)
applies (nilearn 0.14.1), which gave the 871 participants the atlases were downloaded for.

Not applied yet: gate 2, head motion (threshold still provisional in memo 0003), and the rest
of gate 3, which needs the downloaded time series. Add them here when they are confirmed, so
the exclusion log and the API stay one source of truth.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from neurographx.config import load

NO_FILE = "no_filename"


def rater_criteria(root: Path | None = None) -> dict[str, list[str]]:
    """Accepted values per rater column, from configs/qc_criteria.yaml."""
    return load("qc_criteria.yaml", root)["rater_criteria"]


def exclusion_reasons(row: pd.Series, criteria: dict[str, list[str]]) -> list[str]:
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
    return reasons
