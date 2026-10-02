#!/usr/bin/env python3
"""Step 4 of Week 1: download all four atlases for every quality-passing participant.

Usage:
    caffeinate -i python scripts/04_fetch_all_atlases.py      # macOS, stops the Mac sleeping
    python scripts/04_fetch_all_atlases.py --limit 20         # a quick trial on 20 participants

Run 03_pilot_atlas.py first and only continue if it passed.

This is resumable. Files already on disk are skipped, so if it is interrupted,
run the same command again and it carries on where it stopped.

At the end it writes docs/reports/atlas_summary.md, which closes the open items
in decision memo 0001.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

from neurographx.config import load
from neurographx.m1_ingestion.atlas_summary import render, summarise_atlas
from neurographx.m1_ingestion.fetch import parse_strategy
from neurographx.utils.paths import resolve


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="only the first N participants, for a trial run")
    ap.add_argument("--quiet", action="store_true", help="hide per-file download messages")
    args = ap.parse_args()

    import nilearn
    from nilearn.datasets import fetch_abide_pcp

    cfg = load("data.yaml")
    pipeline = cfg["pipeline"]["name"]
    strategy = cfg["pipeline"]["strategy"]
    flags = parse_strategy(strategy)
    raw = resolve(cfg["paths"]["raw"])
    folder = raw / "ABIDE_pcp" / pipeline / strategy

    print(f"Pipeline: {pipeline}   strategy: {strategy}")
    print(f"Atlases: {', '.join(a['label'] for a in cfg['atlases'])}")
    print(f"Files go to: {folder}")
    if args.limit:
        print(f"TRIAL RUN: first {args.limit} participants only")
    print()

    rows = []
    for i, atlas in enumerate(cfg["atlases"], 1):
        key = atlas["key"]
        print(f"[{i}/{len(cfg['atlases'])}] {atlas['label']} ({key})")
        t0 = time.time()
        data = fetch_abide_pcp(
            data_dir=str(raw),
            pipeline=pipeline,
            band_pass_filtering=flags["band_pass_filtering"],
            global_signal_regression=flags["global_signal_regression"],
            derivatives=[key],
            quality_checked=True,
            n_subjects=args.limit,
            verbose=0 if args.quiet else 1,
        )
        arrays = getattr(data, key)
        ids = list(data.phenotypic["FILE_ID"])
        row = summarise_atlas(key, atlas["label"], atlas["family"], arrays, ids, folder)
        rows.append(row)
        print(f"      {row['participants']} participants, {row['regions']} regions, "
              f"{row['size_mb']} MB, {row['invalid_matrices']} invalid, "
              f"{time.time() - t0:.0f} s\n")
        del data, arrays

    meta = {"date": dt.date.today().isoformat(), "pipeline": pipeline,
            "strategy": strategy, "nilearn": nilearn.__version__}
    out = resolve(cfg["paths"]["reports"]) / "atlas_summary.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, meta), encoding="utf-8")
    print(f"Wrote {out}")

    bad = sum(r["invalid_matrices"] for r in rows)
    if bad:
        print(f"\n{bad} invalid matrices. Read the summary before going further.")
        return 1
    print("\nAll four atlases downloaded and every matrix is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
