"""SQLite view of the run log and model registry.

The JSON files written by `m3_model.run_logger` stay the source of truth.
This module loads them into a SQLite database built from `db/schema.sql`, so
the run log and registry can be queried and so a mismatch between the logger
and the schema fails loudly instead of going unnoticed.
"""
import json
import sqlite3
from pathlib import Path

from neurographx.m3_model.run_logger import (
    LOG_PATH,
    REGISTRY_PATH,
    read_registry,
    read_runs,
)

RUN_LOG_COLUMNS = (
    "run_id",
    "timestamp",
    "schema_version",
    "git_commit",
    "environment",
    "dataset",
    "atlas",
    "seed",
    "hyperparameters",
    "metrics",
    "checkpoint_path",
    "data_config",
    "split_sizes",
    "reload_identical",
    "stage",
    "repeat_frozen_measurement",
)
REGISTRY_COLUMNS = (
    "atlas",
    "run_id",
    "checkpoint_path",
    "metrics",
    "registered_at",
    "previous_run_ids",
)
# Columns whose value is a JSON object or array, stored as text.
JSON_COLUMNS = frozenset({
    "environment",
    "hyperparameters",
    "metrics",
    "data_config",
    "split_sizes",
    "previous_run_ids",
})


def connect(db_path, schema_path) -> sqlite3.Connection:
    """Open `db_path`, create the tables if needed and enforce foreign keys."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(Path(schema_path).read_text())
    return conn


def _row(record: dict, columns: tuple, source: str) -> list:
    unknown = sorted(set(record) - set(columns))
    if unknown:
        raise ValueError(f"{source} has fields the schema does not know: {unknown}")
    row = []
    for column in columns:
        value = record.get(column)
        if value is not None and column in JSON_COLUMNS:
            value = json.dumps(value, sort_keys=True)
        row.append(value)
    return row


def import_run_log(conn: sqlite3.Connection, log_path=LOG_PATH) -> int:
    """Load every run record into `run_log`. Returns the number of rows.

    Raises ValueError if a record carries a field with no matching column.
    """
    rows = []
    for record in read_runs(log_path):
        record = {"schema_version": 1, **record}
        rows.append(_row(record, RUN_LOG_COLUMNS, f"run {record.get('run_id')}"))
    marks = ", ".join("?" for _ in RUN_LOG_COLUMNS)
    with conn:
        conn.executemany(
            f"INSERT INTO run_log ({', '.join(RUN_LOG_COLUMNS)}) VALUES ({marks})",
            rows,
        )
    return len(rows)


def import_registry(conn: sqlite3.Connection, registry_path=REGISTRY_PATH) -> int:
    """Load the model registry into `model_registry`. Returns the number of rows.

    Import the run log first: every registry entry must point at a logged run.
    """
    rows = [
        _row(entry, REGISTRY_COLUMNS, f"registry entry {atlas}")
        for atlas, entry in sorted(read_registry(registry_path).items())
    ]
    marks = ", ".join("?" for _ in REGISTRY_COLUMNS)
    with conn:
        conn.executemany(
            f"INSERT INTO model_registry ({', '.join(REGISTRY_COLUMNS)}) VALUES ({marks})",
            rows,
        )
    return len(rows)
