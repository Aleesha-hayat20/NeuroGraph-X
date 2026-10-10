"""The database schema must stay in step with the run logger (issue #20)."""
import json
import sqlite3
from pathlib import Path

import pytest

from neurographx.m3_model import run_logger
from neurographx.utils.db import (
    REGISTRY_COLUMNS,
    RUN_LOG_COLUMNS,
    connect,
    import_registry,
    import_run_log,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"
COMMITTED_LOG = REPO_ROOT / "runs" / "run_log.jsonl"

RECORD = {
    "dataset": "synthetic_brain",
    "atlas": "synthetic200",
    "seed": 42,
    "hyperparameters": {"hidden": 64, "layers": 3},
    "metrics": {"best_val_acc": 0.9},
    "checkpoint_path": "checkpoints/example.pt",
}


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.sqlite", SCHEMA_PATH)
    yield connection
    connection.close()


def table_columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def test_schema_creates_the_three_tables(conn):
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"run_log", "model_registry", "analysis_log"} <= tables


def test_table_columns_match_the_importer(conn):
    assert table_columns(conn, "run_log") == list(RUN_LOG_COLUMNS)
    assert table_columns(conn, "model_registry") == list(REGISTRY_COLUMNS)


def test_run_log_has_a_column_for_every_logger_field(conn):
    provenance = {"timestamp", "schema_version", "git_commit", "environment"}
    logger_fields = set(run_logger.REQUIRED_FIELDS) | provenance
    assert logger_fields <= set(table_columns(conn, "run_log"))


def test_logged_run_and_registered_model_import_cleanly(conn, tmp_path):
    log_path = tmp_path / "run_log.jsonl"
    registry_path = tmp_path / "model_registry.json"
    first = run_logger.log_run({"run_id": "aaaa0001", **RECORD}, log_path)
    second = run_logger.log_run({"run_id": "aaaa0002", **RECORD}, log_path)
    run_logger.register_model(first, log_path, registry_path)
    entry = run_logger.register_model(second, log_path, registry_path)

    assert import_run_log(conn, log_path) == 2
    assert import_registry(conn, registry_path) == 1

    row = conn.execute(
        "SELECT run_id, checkpoint_path, metrics, registered_at, previous_run_ids "
        "FROM model_registry WHERE atlas = 'synthetic200'").fetchone()
    assert row[0] == entry["run_id"] == second
    assert row[1] == entry["checkpoint_path"]
    assert json.loads(row[2]) == entry["metrics"]
    assert row[3] == entry["registered_at"]
    assert json.loads(row[4]) == [first]

    version, environment = conn.execute(
        "SELECT schema_version, environment FROM run_log WHERE run_id = ?",
        (first,)).fetchone()
    assert version == run_logger.SCHEMA_VERSION
    assert "python" in json.loads(environment)


def test_committed_run_log_imports(conn):
    if not COMMITTED_LOG.exists():
        pytest.skip("no committed run log")
    expected = run_logger.read_runs(COMMITTED_LOG)
    assert import_run_log(conn, COMMITTED_LOG) == len(expected)
    stored = {row[0] for row in conn.execute("SELECT run_id FROM run_log")}
    assert stored == {record["run_id"] for record in expected}


def test_unknown_run_field_is_rejected(conn, tmp_path):
    log_path = tmp_path / "run_log.jsonl"
    run_logger.log_run(
        {"run_id": "aaaa0003", "not_in_schema": 1, **RECORD}, log_path)
    with pytest.raises(ValueError, match="not_in_schema"):
        import_run_log(conn, log_path)


def test_registry_cannot_point_at_an_unlogged_run(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO model_registry "
            "(atlas, run_id, checkpoint_path, metrics, registered_at) "
            "VALUES ('cc200', 'missing', 'x.pt', '{}', '2026-10-08T00:00:00+00:00')")


def test_analysis_log_rejects_bad_values(conn, tmp_path):
    log_path = tmp_path / "run_log.jsonl"
    run_logger.log_run({"run_id": "aaaa0004", **RECORD}, log_path)
    import_run_log(conn, log_path)
    insert = (
        "INSERT INTO analysis_log (analysis_id, timestamp, participant_id, atlas, "
        "run_id, prediction, confidence, calibrated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    good = ("an01", "2026-10-08T00:00:00+00:00", "50002", "synthetic200",
            "aaaa0004", "autism", 0.71, 0)
    conn.execute(insert, good)
    for position, bad_value in ((4, "missing"), (5, "maybe"), (6, 1.5), (7, 3)):
        row = list(good)
        row[0] = f"bad{position}"
        row[position] = bad_value
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, row)
