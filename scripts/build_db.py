"""Build a SQLite database from the run log and model registry.

Usage: python scripts/build_db.py [output.sqlite]

The database is rebuilt from the JSON files on every call, so it is a
disposable view and is not committed.
"""
import sys
from pathlib import Path

from neurographx.utils.db import connect, import_registry, import_run_log

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"
DEFAULT_DB = REPO_ROOT / "runs" / "neurographx.sqlite"


def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path, SCHEMA_PATH)
    runs = import_run_log(conn, REPO_ROOT / "runs" / "run_log.jsonl")
    models = import_registry(conn, REPO_ROOT / "runs" / "model_registry.json")
    conn.close()
    print(f"{db_path}: {runs} runs, {models} registered models")


if __name__ == "__main__":
    main()
