"""The participant table served by the API.

Two sources, each used for what it is the authority on (decision memo 0013, part 3):

- **Demographics** (site, group, sex, age, FILE_ID) come from the ABIDE Preprocessed
  phenotypic file named in the active dataset's data.yaml.
- **Quality status** comes from the committed outputs of scripts/05_apply_qc.py:
  data/splits/qc_cohort.csv (included) and docs/reports/exclusion_log.csv (excluded,
  with the gate and every reason). These include the completeness gate, which a live
  screen of the phenotypic file cannot apply, and they are exactly the cohort the
  models were trained and evaluated on.

The **split** (frozen evaluation set or development pool) comes from the frozen-set and
fold files, so the dashboard can say when a participant was used to train the models.

NGX_DATA picks the dataset (memo 0014): the real one, or the synthetic fixture. Nothing
here makes a quality decision; it only joins files that M1 already wrote.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from neurographx import datasource
from neurographx.api.errors import DataUnavailable
from neurographx.m1_ingestion import metadata as md

GROUPS = {1: "autism", 2: "control"}  # DX_GROUP coding, as in metadata.DX_LABELS
SEXES = {1: "male", 2: "female"}  # SEX coding, as in metadata.SEX_LABELS
NO_FILE = "no_filename"

_cache: dict[tuple, list[dict]] = {}


def table_path(root: Path | None = None) -> Path:
    """Where the phenotypic file lives, according to the active dataset's data.yaml."""
    return datasource.phenotypic_table(root)


def participant_id(sub_id) -> str:
    """ABIDE subject ID as a 7-digit string, the form inference.predict uses (0050003)."""
    return f"{int(sub_id):07d}"


def normalise_id(value: str) -> str | None:
    """'50003' or '0050003' -> '0050003'. Anything that is not digits -> None."""
    value = str(value).strip()
    return participant_id(value) if value.isdigit() else None


def _value(row: pd.Series, column: str):
    """A cell as a plain Python value, or None when the column or value is missing."""
    if column not in row.index or pd.isna(row[column]):
        return None
    value = row[column]
    return value.item() if hasattr(value, "item") else value


def _split_list(text, sep: str) -> list[str]:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return []
    return [part.strip() for part in str(text).split(sep) if part.strip()]


def _mtime(path: Path) -> int | None:
    return path.stat().st_mtime_ns if path.exists() else None


def _read_status(root: Path | None) -> dict[int, dict]:
    """SUB_ID -> quality status, from the committed QC outputs."""
    cohort_path, log_path = datasource.qc_cohort(root), datasource.exclusion_log(root)
    missing = [p.name for p in (cohort_path, log_path) if not p.exists()]
    if missing:
        raise DataUnavailable(
            f"Quality-control outputs not found ({', '.join(missing)}). "
            "Run scripts/05_apply_qc.py first.")
    cohort, log = pd.read_csv(cohort_path), pd.read_csv(log_path)
    status: dict[int, dict] = {}
    for sub in cohort["SUB_ID"]:
        status[int(sub)] = {"qc_status": "included", "exclusion_gate": None,
                            "exclusion_reasons": [], "gates_failed": []}
    for row in log.itertuples(index=False):
        sub = int(row.SUB_ID)
        if sub in status:
            raise DataUnavailable(
                f"Participant {participant_id(sub)} is in both {cohort_path.name} and "
                f"{log_path.name}. Re-run scripts/05_apply_qc.py.")
        status[sub] = {"qc_status": "excluded",
                       "exclusion_gate": str(row.first_gate_failed),
                       "exclusion_reasons": _split_list(row.reasons, ";"),
                       "gates_failed": _split_list(row.gates_failed, ";")}
    return status


def _read_splits(root: Path | None) -> dict[int, str]:
    """SUB_ID -> 'frozen' or 'development'. Missing files simply give no split."""
    splits: dict[int, str] = {}
    folds, frozen = datasource.cv_folds(root), datasource.frozen_set(root)
    if folds.exists():
        splits.update({int(s): "development" for s in pd.read_csv(folds)["SUB_ID"]})
    if frozen.exists():
        splits.update({int(s): "frozen" for s in pd.read_csv(frozen)["SUB_ID"]})
    return splits


def build_records(df: pd.DataFrame, status: dict[int, dict],
                  splits: dict[int, str] | None = None) -> list[dict]:
    """Join the phenotypic table with the quality status, one record per participant."""
    if "SUB_ID" not in df.columns:
        raise DataUnavailable("Participant table unreadable: it has no SUB_ID column.")
    splits = splits or {}
    table_ids = {int(s) for s in df["SUB_ID"]}
    unknown = sorted(table_ids - set(status))
    extra = sorted(set(status) - table_ids)
    if unknown or extra:
        raise DataUnavailable(
            "The quality-control outputs do not match the participant table "
            f"({len(unknown)} participant(s) in neither qc_cohort.csv nor exclusion_log.csv, "
            f"{len(extra)} in the QC outputs but not in the table). "
            "Re-run scripts/05_apply_qc.py.")
    records = []
    for _, row in df.iterrows():
        sub = int(row["SUB_ID"])
        file_id = _value(row, "FILE_ID")
        age = _value(row, "AGE_AT_SCAN")
        st = status[sub]
        records.append({
            "participant_id": participant_id(sub),
            "file_id": None if file_id in (None, NO_FILE) else str(file_id),
            "site": _value(row, "SITE_ID"),
            "group": GROUPS.get(_value(row, "DX_GROUP")),
            "sex": SEXES.get(_value(row, "SEX")),
            "age": None if age is None else round(float(age), 2),
            "qc_status": st["qc_status"],
            "exclusion_gate": st["exclusion_gate"],
            "exclusion_reasons": list(st["exclusion_reasons"]),
            "split": splits.get(sub) if st["qc_status"] == "included" else None,
            "gates_failed": list(st["gates_failed"]),  # for /exclusions; not in Participant
        })
    return records


def load_participants(root: Path | None = None) -> list[dict]:
    """Every participant with demographics, quality status and split.

    Read once and reused until any of the files changes. Raises DataUnavailable (503)
    when a file is missing or the files disagree.
    """
    table = table_path(root)
    if not table.exists():
        raise DataUnavailable(
            f"Participant table {table.name} not found in data/raw. "
            "Run scripts/01_fetch_phenotypic.py first, or start the API with "
            "NGX_DATA=fixtures to use the synthetic fixture dataset.")
    sources = (table, datasource.qc_cohort(root), datasource.exclusion_log(root),
               datasource.frozen_set(root), datasource.cv_folds(root))
    key = tuple((str(p), _mtime(p)) for p in sources)
    if key not in _cache:
        try:
            df = md.load_phenotypic(table)
        except (ValueError, pd.errors.ParserError) as err:
            raise DataUnavailable(f"Participant table unreadable: {err}") from err
        records = build_records(df, _read_status(root), _read_splits(root))
        _cache.clear()
        _cache[key] = records
    return _cache[key]


def find_participant(records: list[dict], value: str) -> dict | None:
    """The record for '50003' or '0050003', or None."""
    wanted = normalise_id(value)
    if wanted is None:
        return None
    return next((r for r in records if r["participant_id"] == wanted), None)
