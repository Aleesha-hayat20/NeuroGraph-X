#!/usr/bin/env python3
"""Step 3 of Week 1: pilot one atlas end to end on a handful of participants.

Usage:
    python scripts/03_pilot_atlas.py --n 5

Downloads the region time series for the pilot atlas only, for a small number of
participants, builds one correlation matrix and saves a heatmap. The point is to
prove the whole path works before pulling the other three atlases.

The rois_* derivatives are small .1D text files. Do not request func_preproc,
which is a large .nii.gz volume.
"""

from __future__ import annotations

import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from neurographx.config import load  # noqa: E402
from neurographx.utils.paths import resolve  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5, help="participants to pilot")
    args = ap.parse_args()

    from nilearn.datasets import fetch_abide_pcp

    cfg = load("data.yaml")
    atlas = cfg["pilot_atlas"]
    pipeline = cfg["pipeline"]["name"]
    strategy = cfg["pipeline"]["strategy"]
    raw = resolve(cfg["paths"]["raw"])

    print(f"Pilot atlas: {atlas}   pipeline: {pipeline}   strategy: {strategy}")
    data = fetch_abide_pcp(
        data_dir=str(raw),
        pipeline=pipeline,
        band_pass_filtering="filt" in strategy,
        global_signal_regression="noglobal" not in strategy,
        derivatives=[atlas],
        quality_checked=True,
        n_subjects=args.n,
    )

    series = getattr(data, atlas)
    print(f"Fetched {len(series)} participants")

    ts = np.asarray(series[0])
    print(f"First participant time series shape: {ts.shape}  (timepoints, regions)")
    if ts.ndim != 2 or ts.shape[1] < 2:
        print("Unexpected shape. Inspect the file before continuing.")
        return 1

    corr = np.corrcoef(ts, rowvar=False)
    print(f"Correlation matrix shape: {corr.shape}")
    print(f"Diagonal all close to 1: {np.allclose(np.diag(corr), 1.0)}")
    print(f"Symmetric: {np.allclose(corr, corr.T, equal_nan=True)}")
    print(f"Value range: {np.nanmin(corr):.3f} to {np.nanmax(corr):.3f}")

    out_dir = resolve(cfg["paths"]["reports"]) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, interpolation="nearest")
    ax.set_title(f"Pilot connectivity matrix, {atlas}", loc="left",
                 fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("region")
    ax.set_ylabel("region")
    fig.colorbar(im, ax=ax, shrink=0.82, label="correlation")
    fig.tight_layout()
    path = out_dir / "pilot_connectivity_matrix.png"
    fig.savefig(path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"Saved {path}")

    npy = resolve(cfg["paths"]["interim"]) / "pilot_corr.npy"
    npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(npy, corr)
    print(f"Saved {npy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
