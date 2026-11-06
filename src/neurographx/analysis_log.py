"""The analysis log (decision memo 0013, part 1; backlog W5-05).

One analysis is one prediction for one participant on one atlas, requested through the
API. Each gets its own `analysis_id` and one line in an append-only JSON Lines file:

    runs/analysis_log.jsonl            real data (committed with the demo analyses at release)
    fixtures/runs/analysis_log.jsonl   fixture mode (ignored by git)

"Append-only" means records are only ever added at the end, never changed or deleted, so
the file is the complete history. The SQLite database is rebuilt from it by
scripts/build_db.py (table `analysis_log` in db/schema.sql), like the run log (memo 0008).

This module is the ONLY way analysis records are written. It checks every record before
writing it:

- exactly the ten fields of the `analysis_log` table, with the right types and formats;
- a new, unique `analysis_id`;
- a `run_id` that is in the run log of the same dataset (the model really was trained);
- a `reproduces_analysis_id`, when given, that is already in the analysis log.

Typical use by POST /analyses:

    from neurographx import analysis_log
    out = inference.predict(...)                 # participant_id, atlas, prediction, ...
    record = analysis_log.log_prediction(out)    # checked, written, returned
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from neurographx import datasource
from neurographx.m3_model.run_logger import get_run
from neurographx.m3_model.run_logger import git_commit as current_commit

# The columns of analysis_log in db/schema.sql, in the same order (a test checks it).
FIELDS = (
    "analysis_id",
    "timestamp",
    "participant_id",
    "atlas",
    "run_id",
    "prediction",
    "confidence",
    "calibrated",
    "git_commit",
    "reproduces_analysis_id",
)
ATLASES = ("aal", "cc200", "ho", "dosenbach160")
PREDICTIONS = ("autism", "control")

_ANALYSIS_ID = re.compile(r"^[0-9a-f]{12}$")
_RUN_ID = re.compile(r"^[0-9a-f]{8}$")
_PARTICIPANT_ID = re.compile(r"^[0-9]{7}$")

_lock = threading.Lock()  # FastAPI runs plain endpoints in a thread pool


class AnalysisLogError(ValueError):
    """A record that must not be written, with the reason."""


def new_analysis_id() -> str:
    """12 lowercase hex characters, so it can never be mistaken for an 8-character run_id."""
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Checking a record
# ---------------------------------------------------------------------------

def validate(record: dict) -> None:
    """Raise AnalysisLogError naming the first problem; return None if the record is valid."""
    keys = set(record)
    missing = [f for f in FIELDS if f not in keys]
    unknown = sorted(keys - set(FIELDS))
    if missing:
        raise AnalysisLogError(f"analysis record is missing fields: {missing}")
    if unknown:
        raise AnalysisLogError(f"analysis record has fields the schema does not know: {unknown}")

    def check(ok: bool, message: str) -> None:
        if not ok:
            raise AnalysisLogError(message)

    r = record
    check(isinstance(r["analysis_id"], str) and bool(_ANALYSIS_ID.match(r["analysis_id"])),
          f"analysis_id must be 12 lowercase hex characters, got {r['analysis_id']!r}")
    try:
        stamp = datetime.fromisoformat(str(r["timestamp"]))
    except ValueError:
        stamp = None
    check(stamp is not None and stamp.tzinfo is not None,
          f"timestamp must be ISO 8601 with a time zone, got {r['timestamp']!r}")
    check(isinstance(r["participant_id"], str) and bool(_PARTICIPANT_ID.match(r["participant_id"])),
          f"participant_id must be 7 digits, got {r['participant_id']!r}")
    check(r["atlas"] in ATLASES, f"atlas must be one of {ATLASES}, got {r['atlas']!r}")
    check(isinstance(r["run_id"], str) and bool(_RUN_ID.match(r["run_id"])),
          f"run_id must be 8 lowercase hex characters, got {r['run_id']!r}")
    check(r["prediction"] in PREDICTIONS,
          f"prediction must be 'autism' or 'control', got {r['prediction']!r}")
    conf = r["confidence"]
    check(isinstance(conf, (int, float)) and not isinstance(conf, bool) and 0.5 <= conf <= 1.0,
          f"confidence must be a number from 0.5 to 1, got {conf!r}")
    check(isinstance(r["calibrated"], bool),
          f"calibrated must be true or false, got {r['calibrated']!r}")
    check(r["git_commit"] is None or isinstance(r["git_commit"], str),
          f"git_commit must be text or null, got {r['git_commit']!r}")
    rep = r["reproduces_analysis_id"]
    check(rep is None or (isinstance(rep, str) and bool(_ANALYSIS_ID.match(rep))),
          f"reproduces_analysis_id must be null or an analysis_id, got {rep!r}")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _path(path: Path | None) -> Path:
    return Path(path) if path is not None else datasource.analysis_log()


def read_all(path: Path | None = None) -> list[dict]:
    """Every record, in file order (oldest first). A missing file means no analyses yet."""
    path = _path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def read_analyses(path: Path | None = None, participant_id: str | None = None,
                  atlas: str | None = None) -> list[dict]:
    """Records newest first, optionally filtered.

    Newest first means latest timestamp first; records written in the same second keep
    the order of the file (the later line is the newer one).
    """
    records = list(enumerate(read_all(path)))
    if participant_id is not None:
        records = [(i, r) for i, r in records if r["participant_id"] == participant_id]
    if atlas is not None:
        records = [(i, r) for i, r in records if r["atlas"] == atlas]
    records.sort(key=lambda pair: (pair[1]["timestamp"], pair[0]), reverse=True)
    return [r for _, r in records]


def get_analysis(analysis_id: str, path: Path | None = None) -> dict | None:
    return next((r for r in read_all(path) if r["analysis_id"] == analysis_id), None)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write_analysis(record: dict, path: Path | None = None,
                   run_log_path: Path | None = None) -> dict:
    """Check `record` and append it as one line. Returns the record.

    Raises AnalysisLogError if the record is malformed, its analysis_id is already used,
    its run_id is not in the run log, or it reproduces an analysis that does not exist.
    Nothing is written when any check fails.
    """
    validate(record)
    path = _path(path)
    run_log_path = Path(run_log_path) if run_log_path is not None else datasource.run_log()
    if get_run(record["run_id"], run_log_path) is None:
        raise AnalysisLogError(
            f"run_id {record['run_id']} is not in {run_log_path}; an analysis must name the "
            "training run of the model that made it")
    line = json.dumps({f: record[f] for f in FIELDS})  # serialise first: no half-written line
    with _lock:
        existing = {r["analysis_id"] for r in read_all(path)}
        if record["analysis_id"] in existing:
            raise AnalysisLogError(f"analysis_id {record['analysis_id']} is already in {path}")
        rep = record["reproduces_analysis_id"]
        if rep is not None and rep not in existing:
            raise AnalysisLogError(f"reproduces_analysis_id {rep} is not in {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return record


def make_record(prediction: dict, reproduces_analysis_id: str | None = None,
                commit: str | None = None, timestamp: str | None = None) -> dict:
    """An analysis record from the output of m3_model.inference.predict().

    `prediction` must carry participant_id, atlas, prediction, confidence, calibrated and
    run_id (the prediction-response contract). The id, time and code version are added.
    """
    needed = ("participant_id", "atlas", "prediction", "confidence", "calibrated", "run_id")
    missing = [k for k in needed if k not in prediction]
    if missing:
        raise AnalysisLogError(f"prediction is missing {missing}")
    return {
        "analysis_id": new_analysis_id(),
        "timestamp": timestamp or _now(),
        "participant_id": prediction["participant_id"],
        "atlas": prediction["atlas"],
        "run_id": prediction["run_id"],
        "prediction": prediction["prediction"],
        "confidence": round(float(prediction["confidence"]), 4),
        "calibrated": bool(prediction["calibrated"]),
        "git_commit": commit if commit is not None else current_commit(),
        "reproduces_analysis_id": reproduces_analysis_id,
    }


def log_prediction(prediction: dict, path: Path | None = None, run_log_path: Path | None = None,
                   reproduces_analysis_id: str | None = None) -> dict:
    """make_record + write_analysis: what POST /analyses (and later regenerate) calls."""
    record = make_record(prediction, reproduces_analysis_id=reproduces_analysis_id)
    return write_analysis(record, path, run_log_path)
