"""Build the Week 1 metadata report from the ABIDE phenotypic file.

The report is deliberately defensive about column names. The ABIDE phenotypic
file is not formally documented column by column, so this module reports what
is actually present rather than assuming a schema. Columns it cannot find are
reported as absent instead of causing a failure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

# Documented by nilearn.datasets.fetch_abide_pcp
DX_LABELS = {1: "Autism", 2: "Control"}
SEX_LABELS = {1: "Male", 2: "Female"}

# Values accepted by fetch_abide_pcp(quality_checked=True), nilearn 0.14.1
QC_ACCEPTED = {
    "qc_rater_1": ["OK"],
    "qc_anat_rater_2": ["OK", "maybe"],
    "qc_func_rater_2": ["OK", "maybe"],
    "qc_anat_rater_3": ["OK"],
    "qc_func_rater_3": ["OK"],
}

AGE_BINS = [0, 8, 11, 14, 18, 200]
AGE_LABELS = ["under 8", "8 to 10", "11 to 13", "14 to 17", "18 and over"]

MOTION_PATTERN = re.compile(r"(fd|dvars|motion|displacement)", re.IGNORECASE)


def load_phenotypic(path: Path) -> pd.DataFrame:
    """Read the phenotypic CSV, tolerating the mixed types it contains."""
    return pd.read_csv(path, low_memory=False)


def find_qc_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.lower().startswith("qc_")]


def find_motion_columns(df: pd.DataFrame) -> list[str]:
    out = []
    for c in df.columns:
        if MOTION_PATTERN.search(c) and pd.api.types.is_numeric_dtype(df[c]):
            out.append(c)
    return out


def pick_motion_column(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    """The motion column to plot: the one the QC gate uses if present, else the first found.

    Without a preference the first match in file order is func_dvars, which is not the
    variable the motion gate thresholds. Passing the configured column avoids that.
    """
    found = find_motion_columns(df)
    if preferred and preferred in found:
        return preferred
    return found[0] if found else None


def _counts(df: pd.DataFrame, column: str, labels: dict | None = None) -> pd.DataFrame | None:
    if column not in df.columns:
        return None
    counts = df[column].value_counts(dropna=False).sort_index()
    frame = counts.rename("count").to_frame()
    frame.index.name = column
    if labels:
        frame.insert(0, "label", [labels.get(i, str(i)) for i in frame.index])
    frame["per cent"] = (frame["count"] / len(df) * 100).round(1)
    return frame.reset_index()


def age_bands(df: pd.DataFrame, column: str = "AGE_AT_SCAN") -> pd.DataFrame | None:
    if column not in df.columns:
        return None
    banded = pd.cut(df[column], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    counts = banded.value_counts().reindex(AGE_LABELS).fillna(0).astype(int)
    frame = counts.rename("count").to_frame()
    frame.index.name = "age band"
    frame["per cent"] = (frame["count"] / len(df) * 100).round(1)
    return frame.reset_index()


def site_by_group(df: pd.DataFrame) -> pd.DataFrame | None:
    if "SITE_ID" not in df.columns or "DX_GROUP" not in df.columns:
        return None
    table = pd.crosstab(df["SITE_ID"], df["DX_GROUP"])
    table = table.rename(columns={k: v for k, v in DX_LABELS.items() if k in table.columns})
    table["Total"] = table.sum(axis=1)
    return table.sort_values("Total", ascending=False).reset_index()


def qc_summary(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = find_qc_columns(df)
    if not cols:
        return None
    rows = []
    for c in cols:
        vc = df[c].astype("string").str.strip().value_counts(dropna=False)
        accepted = QC_ACCEPTED.get(c)
        n_ok = int(vc[[v for v in (accepted or []) if v in vc.index]].sum()) if accepted else None
        rows.append(
            {
                "column": c,
                "distinct values": ", ".join(str(v) for v in vc.index[:6]),
                "most common": str(vc.index[0]) if len(vc) else "",
                "count of most common": int(vc.iloc[0]) if len(vc) else 0,
                "accepted values": ", ".join(accepted) if accepted else "not in the nilearn filter",
                "passing": n_ok if n_ok is not None else "",
            }
        )
    return pd.DataFrame(rows)


def motion_summary(df: pd.DataFrame) -> pd.DataFrame | None:
    cols = find_motion_columns(df)
    if not cols:
        return None
    described = df[cols].describe().T
    described = described[["count", "mean", "std", "min", "50%", "max"]]
    described = described.round(3).reset_index()
    described = described.rename(columns={"index": "column", "50%": "median"})
    return described


def would_pass_all_raters(df: pd.DataFrame) -> dict[str, Any]:
    """How many participants would survive the standard rater filter."""
    present = [c for c in QC_ACCEPTED if c in df.columns]
    if not present:
        return {"applicable": False}
    mask = pd.Series(True, index=df.index)
    per_column = {}
    for c in present:
        values = df[c].astype("string").str.strip()
        ok = values.isin(QC_ACCEPTED[c])
        per_column[c] = int(ok.sum())
        mask &= ok
    return {
        "applicable": True,
        "columns_used": present,
        "per_column_passing": per_column,
        "passing_all": int(mask.sum()),
        "total": int(len(df)),
    }
