#!/usr/bin/env python3
"""Step 1 of Week 1: download the ABIDE phenotypic file and list its columns.

Usage:
    python scripts/01_fetch_phenotypic.py

Downloads one small CSV into data/raw/ and prints every column name it contains.
It does not download any imaging data.
"""

from __future__ import annotations

import sys

import pandas as pd

from neurographx.config import load
from neurographx.m1_ingestion.fetch import download, phenotypic_url
from neurographx.utils.paths import resolve


def main() -> int:
    cfg = load("data.yaml")
    ds = cfg["dataset"]
    url = phenotypic_url(ds["base_url"], ds["phenotypic_file"])
    target = resolve(cfg["paths"]["raw"]) / ds["phenotypic_file"]

    if target.exists():
        print(f"Already present, skipping download: {target}")
    else:
        print(f"Downloading {url}")
        download(url, target)
        print(f"Saved to {target}")

    df = pd.read_csv(target, low_memory=False)
    print(f"\nRows: {len(df)}    Columns: {len(df.columns)}\n")
    print("Column names:")
    for i, c in enumerate(df.columns, 1):
        print(f"  {i:3d}. {c}")

    qc = [c for c in df.columns if c.lower().startswith("qc_")]
    print(f"\nQuality control columns found ({len(qc)}): {', '.join(qc) if qc else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
