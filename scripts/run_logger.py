"""Minimal run logger (seed of L5).

Every training run appends ONE JSON line to runs/run_log.jsonl containing its
configuration and result. Later this maps directly onto Alishba's run-log
table in the database schema.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("runs/run_log.jsonl")


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def log_run(record: dict, path: Path = LOG_PATH) -> str:
    """Append a run record. `record` should contain run_id, dataset, atlas,
    seed, hyperparameters, metrics and checkpoint_path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **record,
    }
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record["run_id"]


def read_runs(path: Path = LOG_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
