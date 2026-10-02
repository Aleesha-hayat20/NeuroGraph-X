#!/usr/bin/env python3
"""Step 3 of Week 1: pilot one atlas end to end on a handful of participants.

Usage:
    python scripts/03_pilot_atlas.py --n 5

Downloads the region time series for the pilot atlas only, for a few
participants, checks every one, and saves a heatmap of the first. The point is
to prove the whole path works before pulling all four atlases for everyone.

The rois_* derivatives are small .1D text files. Never request func_preproc,
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
from neurographx.m1_ingestion.fetch import parse_strategy  # noqa: E402
from neurographx.m2_connectome import connectivity as cx  # noqa: E402
from neurographx.utils.paths import resolve  # noqa: E402


def yn(flag) -> str:
    return "yes" if flag else "NO"


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
    flags = parse_strategy(strategy)

    print(f"Pilot atlas: {atlas}   pipeline: {pipeline}   strategy: {strategy}")
    print(f"  band-pass filtering: {flags['band_pass_filtering']}   "
          f"global signal regression: {flags['global_signal_regression']}\n")

    data = fetch_abide_pcp(
        data_dir=str(raw),
        pipeline=pipeline,
        band_pass_filtering=flags["band_pass_filtering"],
        global_signal_regression=flags["global_signal_regression"],
        derivatives=[atlas],
        quality_checked=True,
        n_subjects=args.n,
        verbose=0,
    )
    series = getattr(data, atlas)
    ids = list(data.phenotypic["FILE_ID"])
    folder = raw / "ABIDE_pcp" / pipeline / strategy
    print(f"Fetched {len(series)} participants into {folder}\n")

    first_corr, results = None, []
    for fid, ts in zip(ids, series):
        ts = np.asarray(ts)
        if ts.ndim == 1:
            ts = ts.reshape(1, -1)
        path = folder / f"{fid}_{atlas}.1D"
        size_kb = path.stat().st_size / 1024 if path.exists() else float("nan")
        zv = cx.zero_variance_regions(ts)
        corr = cx.correlation_matrix(ts)
        rep = cx.check_matrix(corr, zv)
        ok = cx.is_valid(rep)
        results.append(ok)
        if first_corr is None:
            first_corr, first_id = corr, fid

        print(f"Participant {fid}")
        print(f"  time series ............ {ts.shape[0]} timepoints x {ts.shape[1]} regions")
        print(f"  file size .............. {size_kb:.1f} KB")
        print(f"  zero-variance regions .. {len(zv)}"
              + (f"  (indices {list(zv)[:10]})" if len(zv) else ""))
        print(f"  connectivity matrix .... {rep['shape'][0]} x {rep['shape'][1]}")
        print(f"  square ................. {yn(rep['square'])}")
        print(f"  symmetric .............. {yn(rep['symmetric'])}")
        print(f"  diagonal equals 1 ...... {yn(rep['diagonal_ones'])}"
              + ("  (regions with signal)" if len(zv) else ""))
        print(f"  values within -1 to 1 .. {yn(rep['min'] >= -1 - 1e-9 and rep['max'] <= 1 + 1e-9)}"
              f"  (min {rep['min']:.3f}, max {rep['max']:.3f})")
        if rep["nan_cells"]:
            why = ("all caused by the zero-variance regions above"
                   if rep["nan_explained_by_zero_variance"] else "NOT explained, investigate")
            print(f"  NaN cells .............. {rep['nan_cells']}  ({why})")
        print(f"  RESULT ................. {'VALID' if ok else 'INVALID, investigate'}\n")

    out_dir = resolve(cfg["paths"]["reports"]) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(first_corr, cmap="RdBu_r", vmin=-1, vmax=1, interpolation="nearest")
    ax.set_title(f"Pilot connectivity matrix, {atlas}, {first_id}", loc="left",
                 fontsize=10.5, fontweight="bold", pad=10)
    ax.set_xlabel("region")
    ax.set_ylabel("region")
    fig.colorbar(im, ax=ax, shrink=0.82, label="Pearson correlation")
    fig.tight_layout()
    fig_path = out_dir / "pilot_connectivity_matrix.png"
    fig.savefig(fig_path, bbox_inches="tight", dpi=200)
    plt.close(fig)

    npy = resolve(cfg["paths"]["interim"]) / "pilot_corr.npy"
    npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(npy, first_corr)

    n_ok = sum(results)
    print(f"Summary: {n_ok} of {len(results)} pilot matrices valid")
    print(f"Saved {fig_path}")
    print(f"Saved {npy}")
    if n_ok == len(results):
        print("\nPilot passed. Safe to run scripts/04_fetch_all_atlases.py")
        return 0
    print("\nPilot did NOT fully pass. Do not run the full download until this is understood.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
