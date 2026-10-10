#!/usr/bin/env python3
"""Week 2, step 7: build the connectome matrices for all four atlases.

Usage:
    python scripts/07_build_connectomes.py            # build, or reuse the cache
    python scripts/07_build_connectomes.py --force    # rebuild everything

For every participant in the QC cohort and every configured atlas, computes the
Pearson correlation matrix and its Fisher z transform and stores one file per
atlas under data/processed/connectomes/. Running it again with unchanged inputs
takes seconds, because the stored files are reused.

Writes docs/reports/connectome_summary.md and a figure of the mean z matrix per
atlas, docs/reports/figures/mean_connectomes.png.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from neurographx.config import load  # noqa: E402
from neurographx.m2_connectome.engine import ENGINE_VERSION, build_atlas  # noqa: E402
from neurographx.utils.paths import project_root, resolve  # noqa: E402


def _progress(label: str):
    def report(k: int, n: int) -> None:
        if k == n or k % 100 == 0:
            print(f"      {label}: {k}/{n}", flush=True)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore the cache and rebuild")
    args = ap.parse_args()

    cfg = load("data.yaml")
    cc = cfg["connectome"]
    pipeline, strategy = cfg["pipeline"]["name"], cfg["pipeline"]["strategy"]
    ts_folder = resolve(cfg["paths"]["raw"]) / "ABIDE_pcp" / pipeline / strategy
    out_dir = resolve(cc["output_dir"])
    cohort_path = resolve(cfg["cohort"]["file"])
    if not cohort_path.exists():
        print("QC cohort not found. Run scripts/05_apply_qc.py first.")
        return 1
    cohort = pd.read_csv(cohort_path)
    print(f"Cohort: {len(cohort)} participants   pipeline: {pipeline}   strategy: {strategy}")
    print(f"Engine version {ENGINE_VERSION}, output in {out_dir}\n")

    rows, sets = [], []
    for i, atlas in enumerate(cfg["atlases"], 1):
        key = atlas["key"]
        print(f"[{i}/{len(cfg['atlases'])}] {atlas['label']} ({key})")
        t0 = time.time()
        cset, status = build_atlas(key, cohort, ts_folder, out_dir, pipeline, strategy,
                                   clip=cc["fisher_clip"], dtype=cc["dtype"],
                                   force=args.force, label=atlas["label"],
                                   progress=_progress(key))
        secs = time.time() - t0
        npz = out_dir / f"{pipeline}_{strategy}" / f"{key}.npz"
        z = cset.z_triu
        nan_edges = int(np.isnan(z).any(axis=0).sum())
        rows.append({
            "Atlas": atlas["label"], "Key": key, "Participants": len(cset),
            "Nodes": cset.n_regions, "Edges": cset.n_edges,
            "Participants with flat regions": int(cset.zero_var.any(axis=1).sum()),
            "Edges NaN in at least one participant": nan_edges,
            "Mean z (finite)": round(float(np.nanmean(z)), 3),
            "Size MB": round(npz.stat().st_size / 1e6, 1),
            "Status": status, "Seconds": round(secs, 1),
        })
        sets.append((atlas["label"], cset))
        print(f"      {status}: {len(cset)} x {cset.n_regions} nodes, {secs:.1f} s\n")

    reports = resolve(cfg["paths"]["reports"])
    fig, axes = plt.subplots(1, len(sets), figsize=(4.2 * len(sets), 4.2))
    for ax, (label, cset) in zip(np.atleast_1d(axes), sets):
        mean_z = np.nanmean(cset.stack("z"), axis=0)
        im = ax.imshow(mean_z, cmap="RdBu_r", vmin=-1, vmax=1, interpolation="nearest")
        ax.set_title(f"{label}, {cset.n_regions} nodes", loc="left", fontsize=10,
                     fontweight="bold")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.8, label="mean Fisher z across the cohort")
    fig.suptitle("Mean connectome per atlas", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    fig_path = reports / "figures" / "mean_connectomes.png"
    fig.savefig(fig_path, bbox_inches="tight", dpi=160)
    plt.close(fig)

    table = pd.DataFrame(rows)
    rel = out_dir.relative_to(project_root())
    text = "\n".join([
        "# Connectome Engine Summary",
        "",
        f"**Generated:** {dt.date.today().isoformat()}  ",
        f"**Engine version:** {ENGINE_VERSION}  ",
        f"**Pipeline:** {pipeline}  **Strategy:** {strategy}  ",
        f"**Cohort:** `{cfg['cohort']['file']}`, {len(cohort)} participants  ",
        f"**Stored in:** `{rel}/{pipeline}_{strategy}/` (not committed, rebuild with "
        "`python scripts/07_build_connectomes.py`)",
        "",
        "Design and conventions: `docs/decisions/0006-connectome-engine.md`. Independent",
        "check of a sample: `docs/reports/connectome_verification.md`.",
        "",
        table.drop(columns=["Seconds"]).to_markdown(index=False),
        "",
        "- **Nodes** is the graph size for that atlas and **Edges** is nodes x (nodes - 1) / 2,",
        "  the number of distinct region pairs stored per participant.",
        "- **Edges NaN in at least one participant** counts region pairs that touch a flat",
        "  region in somebody. They are NaN on disk and handled by the policy in memo 0006.",
        "- **Status** says whether this run computed the matrices or reused the cache.",
        "",
        "![Mean connectome per atlas](figures/mean_connectomes.png)",
        "",
    ])
    (reports / "connectome_summary.md").write_text(text, encoding="utf-8")
    print(table.to_string(index=False))
    print(f"\nWrote {reports / 'connectome_summary.md'}\nWrote {fig_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
