#!/usr/bin/env python3
"""Week 2, step 6: draw the frozen evaluation set ONCE, and the development folds.

Usage:
    python scripts/06_draw_frozen_set.py

Reads data/splits/qc_cohort.csv (from 05_apply_qc.py) and writes:

    data/frozen/frozen_eval_100.csv         100 subject identifiers, committed
    data/frozen/frozen_eval_100.meta.json   seed, method, allocation, hashes, committed
    data/splits/cv5_folds.csv               development pool with a fold column, committed

If the frozen file already exists, the script does NOT redraw it. It only checks
that the existing file still matches its recorded hash, and (re)writes the folds.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from neurographx.config import load
from neurographx.m1_ingestion.splits import (
    assert_no_leakage,
    make_folds,
    sha256_text,
    stratified_draw,
    write_frozen,
)
from neurographx.utils.paths import resolve


def main() -> int:
    cfg = load("data.yaml")
    fz = cfg["frozen_evaluation_set"]
    dv = cfg["development_splits"]
    cohort_path = resolve(cfg["cohort"]["file"])
    csv_path, meta_path = resolve(fz["file"]), resolve(fz["meta"])
    if not cohort_path.exists():
        print("QC cohort not found. Run scripts/05_apply_qc.py first.")
        return 1
    cohort = pd.read_csv(cohort_path)

    if csv_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if sha256_text(csv_path) != meta["frozen_sha256"]:
            print("STOP: the frozen file no longer matches its recorded hash.")
            return 1
        print(f"Frozen set already exists and matches its hash: {csv_path}")
        print("It is never regenerated. Skipping the draw.")
        frozen = pd.read_csv(csv_path)
    else:
        frozen, table = stratified_draw(cohort, fz["size"], fz["stratify_by"], fz["seed"])
        meta = write_frozen(frozen, table, csv_path, meta_path, cohort_path,
                            fz["seed"], fz["stratify_by"])
        print(f"Drew {meta['size']} of {meta['cohort_size']} with seed {meta['seed']}")
        print(table.to_string(index=False))

    pool = cohort[~cohort["SUB_ID"].isin(frozen["SUB_ID"])]
    folds = make_folds(pool, dv["folds"], dv["stratify_by"], dv["seed"])
    assert_no_leakage(folds, frozen, context="cv5_folds.csv")
    folds_path = resolve(dv["file"])
    folds.to_csv(folds_path, index=False, lineterminator="\n")

    print(f"\nFrozen set ........ {len(frozen)}  "
          f"(autism {int((frozen.DX_GROUP == 1).sum())}, "
          f"control {int((frozen.DX_GROUP == 2).sum())}, "
          f"{frozen.SITE_ID.nunique()} sites)")
    print(f"Development pool .. {len(pool)} in {dv['folds']} folds: "
          f"{folds['fold'].value_counts().sort_index().to_dict()}")
    print("Leakage check ..... passed")
    print(f"\nWrote {csv_path}\nWrote {meta_path}\nWrote {folds_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
