#!/usr/bin/env python3
"""Build the fixture dataset (decision memo 0014): a small SYNTHETIC cohort in the real formats.

Usage (from the repository root):
    python scripts/build_fixtures.py              # write fixtures/ (refuses if it exists)
    python scripts/build_fixtures.py --force      # rebuild fixtures/ from scratch
    python scripts/build_fixtures.py --skip-model # no PyTorch needed; no model files

Writes, under fixtures/, the same layout as the repository:

    configs/data.yaml                                       fixture copy of the data config
    data/raw/Phenotypic_V1_0b_preprocessed1.csv             24 invented participants
    data/splits/qc_cohort.csv, cv5_folds.csv                via m1_ingestion (real rules)
    data/frozen/frozen_eval_6.csv (+ .meta.json)            via m1_ingestion.splits
    docs/reports/exclusion_log.csv                          via m1_ingestion.qc
    data/processed/connectomes/cpac_filt_global/rois_cc200.npz/.json, rois_ho.npz/.json
    runs/run_log.jsonl, runs/model_registry.json            via m3_model.run_logger
    checkpoints/cc200_<run_id>.pt                           tiny GCN
    README.md, MANIFEST.json                                description and file hashes

Then use it with one setting:  NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neurographx.datasource import FIXTURE_DIR
from neurographx.fixture_data import build
from neurographx.utils.paths import project_root


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None,
                    help="output folder (default: fixtures/ in the repository)")
    ap.add_argument("--force", action="store_true", help="delete and rebuild an existing fixture")
    ap.add_argument("--skip-model", action="store_true",
                    help="do not train the tiny model (no PyTorch needed)")
    args = ap.parse_args()

    out = args.out or project_root() / FIXTURE_DIR
    try:
        summary = build(out, train_model=not args.skip_model, force=args.force)
    except FileExistsError as err:
        print(f"STOP: {err}")
        return 1
    print(f"\nFixture dataset written to {out}")
    print(f"{summary['participants']} participants: {summary['retained']} retained, "
          f"{summary['excluded']} excluded; frozen {summary['frozen']}, "
          f"development {summary['development']}")
    print("Next: pytest tests/test_fixture_data.py tests/test_datasource.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
