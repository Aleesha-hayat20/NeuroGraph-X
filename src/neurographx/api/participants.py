"""The participant table served by the API.

Reads the ABIDE Preprocessed phenotypic file named in configs/data.yaml with M1's loader,
and asks M1's screen (m1_ingestion/screening.py) for each participant's quality status.
This module only reshapes those results for the API. It makes no quality decisions itself.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from neurographx.config import load
from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion import screening
from neurographx.utils.paths import resolve

GROUPS = {1: "autism", 2: "control"}  # DX_GROUP coding, as in metadata.DX_LABELS
SEXES = {1: "male", 2: "female"}  # SEX coding, as in metadata.SEX_LABELS

_cache: dict[tuple, list[dict]] = {}


def table_path(root: Path | None = None) -> Path:
    """Where the phenotypic file lives, according to configs/data.yaml."""
    cfg = load("data.yaml", root)
    return resolve(cfg["paths"]["raw"], root) / cfg["dataset"]["phenotypic_file"]


def participant_id(sub_id) -> str:
    """ABIDE subject ID as a 7-digit string, the form inference.predict uses (0050003)."""
    return f"{int(sub_id):07d}"


def _value(row: pd.Series, column: str):
    """A cell as a plain Python value, or None when the column or value is missing."""
    if column not in row.index or pd.isna(row[column]):
        return None
    value = row[column]
    return value.item() if hasattr(value, "item") else value


def build_records(df: pd.DataFrame, criteria: dict[str, list[str]],
                  motion: dict | None = None) -> list[dict]:
    if "SUB_ID" not in df.columns:
        raise ValueError("participant table has no SUB_ID column")
    records = []
    for _, row in df.iterrows():
        reasons = screening.exclusion_reasons(row, criteria, motion)
        file_id = _value(row, "FILE_ID")
        age = _value(row, "AGE_AT_SCAN")
        records.append(
            {
                "participant_id": participant_id(row["SUB_ID"]),
                "file_id": None if file_id in (None, screening.NO_FILE) else str(file_id),
                "site": _value(row, "SITE_ID"),
                "group": GROUPS.get(_value(row, "DX_GROUP")),
                "sex": SEXES.get(_value(row, "SEX")),
                "age": None if age is None else round(float(age), 2),
                "qc_status": "excluded" if reasons else "included",
                "exclusion_reasons": reasons,
            }
        )
    return records


def load_participants(path: Path, criteria: dict[str, list[str]],
                      motion: dict | None = None) -> list[dict]:
    """Read the table once and reuse it until the file or the rules change."""
    rules = tuple((c, tuple(v)) for c, v in sorted(criteria.items()))
    rules += (tuple(sorted(motion.items())),) if motion else ()
    key = (str(path), path.stat().st_mtime, rules)
    if key not in _cache:
        _cache.clear()
        _cache[key] = build_records(md.load_phenotypic(path), criteria, motion)
    return _cache[key]
