"""Build a SQLite database from the run log, the model registry and the analysis log.

Usage (from the repository root):
    python scripts/build_db.py                    # active dataset (NGX_DATA), default path
    python scripts/build_db.py --data fixtures    # the fixture dataset (memo 0014)
    python scripts/build_db.py out.sqlite         # write somewhere else

Default output: runs/neurographx.sqlite under the dataset's root (fixtures/runs/ for the
fixture). The database is rebuilt from the JSON files on every call, so it is a
disposable view and is never committed (memos 0008 and 0013).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from neurographx import datasource
from neurographx.utils.db import (
    connect,
    import_analysis_log,
    import_registry,
    import_run_log,
)
from neurographx.utils.paths import project_root

SCHEMA_PATH = project_root() / "db" / "schema.sql"
DB_NAME = "neurographx.sqlite"


def build(root: Path, db_path: Path) -> dict[str, int]:
    """Rebuild `db_path` from the logs under `root`. Returns the row count per table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path, SCHEMA_PATH)
    try:
        counts = {
            "run_log": import_run_log(conn, datasource.run_log(root)),
            "model_registry": import_registry(conn, datasource.model_registry(root)),
            "analysis_log": import_analysis_log(conn, datasource.analysis_log(root)),
        }
    finally:
        conn.close()
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", type=Path, help=f"output file (default runs/{DB_NAME})")
    ap.add_argument("--data", choices=datasource.MODES,
                    help="dataset to read (default: NGX_DATA, or real)")
    args = ap.parse_args()

    if args.data:
        os.environ["NGX_DATA"] = args.data
    root = datasource.data_root()
    db_path = args.out or root / "runs" / DB_NAME
    counts = build(root, db_path)
    print(f"{db_path}: {counts['run_log']} runs, {counts['model_registry']} registered "
          f"models, {counts['analysis_log']} analyses ({datasource.mode()} data)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
