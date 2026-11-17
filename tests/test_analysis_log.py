"""The analysis log writer and its SQLite view (memo 0013; backlog W5-05, W5-06).

Runs on a private copy of the fixture dataset, whose run log holds real run IDs, so the
"run_id must be in the run log" rule is tested against genuine records.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import threading

import pytest

from neurographx import analysis_log as al
from neurographx.m3_model.run_logger import read_registry
from neurographx.utils.db import (
    ANALYSIS_COLUMNS,
    connect,
    import_analysis_log,
    import_registry,
    import_run_log,
)
from neurographx.utils.paths import project_root

SCHEMA = project_root() / "db" / "schema.sql"


@pytest.fixture
def paths(fixture_root):
    """(analysis log, run log, registered run_id) inside the private fixture copy."""
    run_id = read_registry(fixture_root / "runs/model_registry.json")["cc200"]["run_id"]
    return fixture_root / "runs/analysis_log.jsonl", fixture_root / "runs/run_log.jsonl", run_id


def prediction(run_id: str, **overrides) -> dict:
    """The shape inference.predict() returns."""
    base = {"participant_id": "0090001", "atlas": "cc200", "prediction": "autism",
            "confidence": 0.8123456, "calibrated": False, "run_id": run_id}
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def test_log_prediction_writes_one_complete_line(paths):
    log, runs, run_id = paths
    record = al.log_prediction(prediction(run_id), log, runs)
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert list(stored) == list(al.FIELDS)           # exactly the ten fields, in order
    assert stored == record
    assert len(record["analysis_id"]) == 12
    assert record["confidence"] == 0.8123             # rounded to 4 decimals
    assert record["reproduces_analysis_id"] is None
    assert record["timestamp"].endswith("+00:00")


def test_records_are_appended_never_rewritten(paths):
    log, runs, run_id = paths
    first = al.log_prediction(prediction(run_id), log, runs)
    before = log.read_text()
    al.log_prediction(prediction(run_id, participant_id="0090003"), log, runs)
    after = log.read_text()
    assert after.startswith(before)
    assert [r["analysis_id"] for r in al.read_all(log)][0] == first["analysis_id"]


def test_ids_are_unique_and_never_look_like_run_ids():
    ids = {al.new_analysis_id() for _ in range(2000)}
    assert len(ids) == 2000
    assert all(len(i) == 12 and int(i, 16) >= 0 for i in ids)


@pytest.mark.parametrize("field, bad, message", [
    ("analysis_id", "ABC", "analysis_id"),
    ("timestamp", "yesterday", "timestamp"),
    ("timestamp", "2026-10-27T10:00:00", "time zone"),
    ("participant_id", "50003", "7 digits"),
    ("atlas", "cc400", "atlas"),
    ("run_id", "not-a-run", "run_id"),
    ("prediction", "ASD", "prediction"),
    ("confidence", 0.3, "0.5 to 1"),
    ("confidence", True, "0.5 to 1"),
    ("calibrated", "no", "calibrated"),
    ("git_commit", 123, "git_commit"),
    ("reproduces_analysis_id", "x", "reproduces_analysis_id"),
])
def test_malformed_records_are_refused_and_nothing_is_written(paths, field, bad, message):
    log, runs, run_id = paths
    record = al.make_record(prediction(run_id))
    record[field] = bad
    with pytest.raises(al.AnalysisLogError, match=message):
        al.write_analysis(record, log, runs)
    assert not log.exists()


def test_missing_and_unknown_fields_are_refused(paths):
    log, runs, run_id = paths
    record = al.make_record(prediction(run_id))
    with pytest.raises(al.AnalysisLogError, match="missing"):
        al.write_analysis({k: v for k, v in record.items() if k != "git_commit"}, log, runs)
    with pytest.raises(al.AnalysisLogError, match="does not know"):
        al.write_analysis({**record, "notes": "x"}, log, runs)


def test_run_id_must_be_a_logged_training_run(paths):
    log, runs, run_id = paths
    with pytest.raises(al.AnalysisLogError, match="not in"):
        al.log_prediction(prediction("0000beef"), log, runs)
    assert not log.exists()


def test_duplicate_analysis_id_is_refused(paths):
    log, runs, run_id = paths
    record = al.write_analysis(al.make_record(prediction(run_id)), log, runs)
    with pytest.raises(al.AnalysisLogError, match="already"):
        al.write_analysis(dict(record), log, runs)
    assert len(al.read_all(log)) == 1


def test_a_reproduction_must_point_at_an_existing_analysis(paths):
    log, runs, run_id = paths
    with pytest.raises(al.AnalysisLogError, match="reproduces_analysis_id"):
        al.log_prediction(prediction(run_id), log, runs, reproduces_analysis_id="aaaaaaaaaaaa")
    original = al.log_prediction(prediction(run_id), log, runs)
    again = al.log_prediction(prediction(run_id), log, runs,
                              reproduces_analysis_id=original["analysis_id"])
    assert again["reproduces_analysis_id"] == original["analysis_id"]


def test_prediction_missing_a_field_is_refused(paths):
    _, _, run_id = paths
    with pytest.raises(al.AnalysisLogError, match="run_id"):
        al.make_record({k: v for k, v in prediction(run_id).items() if k != "run_id"})


def test_concurrent_writers_never_interleave_lines(paths):
    log, runs, run_id = paths

    def write_many():
        for _ in range(25):
            al.log_prediction(prediction(run_id), log, runs)

    threads = [threading.Thread(target=write_many) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    records = al.read_all(log)                        # every line parses
    assert len(records) == 100
    assert len({r["analysis_id"] for r in records}) == 100


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def test_read_analyses_is_newest_first_and_filters(paths):
    log, runs, run_id = paths
    a = al.write_analysis(al.make_record(prediction(run_id), timestamp="2026-10-27T09:00:00+00:00"),
                          log, runs)
    b = al.write_analysis(al.make_record(prediction(run_id, participant_id="0090003"),
                                         timestamp="2026-10-27T10:00:00+00:00"), log, runs)
    c = al.write_analysis(al.make_record(prediction(run_id), timestamp="2026-10-27T10:00:00+00:00"),
                          log, runs)                   # same second as b, written later
    assert [r["analysis_id"] for r in al.read_analyses(log)] == \
        [c["analysis_id"], b["analysis_id"], a["analysis_id"]]
    assert [r["analysis_id"] for r in al.read_analyses(log, participant_id="0090001")] == \
        [c["analysis_id"], a["analysis_id"]]
    assert al.read_analyses(log, atlas="ho") == []
    assert al.get_analysis(b["analysis_id"], log) == b
    assert al.get_analysis("ffffffffffff", log) is None


def test_missing_log_means_no_analyses(tmp_path):
    assert al.read_all(tmp_path / "nothing.jsonl") == []


# ---------------------------------------------------------------------------
# SQLite (W5-06)
# ---------------------------------------------------------------------------

def test_writer_fields_are_the_schema_columns():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA.read_text())
    columns = [row[1] for row in conn.execute("PRAGMA table_info(analysis_log)")]
    assert columns == list(al.FIELDS) == list(ANALYSIS_COLUMNS)


def test_analysis_log_imports_with_foreign_keys(paths, tmp_path):
    log, runs, run_id = paths
    original = al.log_prediction(prediction(run_id, calibrated=True), log, runs)
    al.log_prediction(prediction(run_id), log, runs,
                      reproduces_analysis_id=original["analysis_id"])
    conn = connect(tmp_path / "t.sqlite", SCHEMA)
    import_run_log(conn, runs)
    import_registry(conn, runs.parent / "model_registry.json")
    assert import_analysis_log(conn, log) == 2
    rows = conn.execute("SELECT analysis_id, calibrated, reproduces_analysis_id, run_id "
                        "FROM analysis_log ORDER BY rowid").fetchall()
    assert rows[0] == (original["analysis_id"], 1, None, run_id)
    assert rows[1][2] == original["analysis_id"]
    joined = conn.execute("SELECT r.stage FROM analysis_log a JOIN run_log r USING (run_id)")
    assert {row[0] for row in joined} == {"final"}
    conn.close()


def test_import_rejects_an_analysis_of_an_unlogged_run(tmp_path):
    """The database refuses what the writer refuses, even if the file was edited by hand."""
    log = tmp_path / "analysis_log.jsonl"
    record = {**al.make_record(prediction("0000beef")), "git_commit": None}
    log.write_text(json.dumps(record) + "\n")
    conn = connect(tmp_path / "t.sqlite", SCHEMA)
    with pytest.raises(sqlite3.IntegrityError):
        import_analysis_log(conn, log)
    conn.close()


def test_import_rejects_unknown_fields(tmp_path):
    log = tmp_path / "analysis_log.jsonl"
    log.write_text(json.dumps({"analysis_id": "aaaaaaaaaaaa", "extra": 1}) + "\n")
    conn = connect(tmp_path / "t.sqlite", SCHEMA)
    with pytest.raises(ValueError, match="does not know"):
        import_analysis_log(conn, log)
    conn.close()


def _build_db_module():
    spec = importlib.util.spec_from_file_location("build_db",
                                                  project_root() / "scripts" / "build_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_db_rebuilds_all_three_tables(paths, tmp_path):
    log, runs, run_id = paths
    al.log_prediction(prediction(run_id), log, runs)
    out = tmp_path / "rebuilt.sqlite"
    counts = _build_db_module().build(log.parents[1], out)
    assert counts == {"run_log": 2, "model_registry": 1, "analysis_log": 1}
    counts_again = _build_db_module().build(log.parents[1], out)   # rebuilt, not appended
    assert counts_again == counts
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM analysis_log").fetchone() == (1,)
    conn.close()


def test_build_db_command_line_on_the_fixture(tmp_path):
    out = tmp_path / "fixture.sqlite"
    result = subprocess.run(
        [sys.executable, "scripts/build_db.py", str(out), "--data", "fixtures"],
        capture_output=True, text=True, cwd=project_root(), check=True)
    # fixture mode is used for development, so analyses may already be recorded there
    log = project_root() / "fixtures/runs/analysis_log.jsonl"
    n = sum(1 for line in log.read_text().splitlines() if line.strip()) if log.exists() else 0
    assert f"2 runs, 1 registered models, {n} analyses (fixtures data)" in result.stdout
    assert out.exists()
