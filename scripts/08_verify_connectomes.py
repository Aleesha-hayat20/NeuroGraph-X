#!/usr/bin/env python3
"""Week 2, step 8: independently recompute a sample of stored matrices.

Usage:
    python scripts/08_verify_connectomes.py

For each atlas, picks a seeded random sample of participants (always including
at least one with a flat region when the atlas has any), recomputes their
matrices by independent routes (see neurographx.m2_connectome.verify) and
compares them with what the engine stored. Writes
docs/reports/connectome_verification.md. Exits non-zero if anything disagrees.
"""

from __future__ import annotations

import datetime as dt
import sys

import numpy as np
import pandas as pd

from neurographx.config import load
from neurographx.m2_connectome import verify as vf
from neurographx.m2_connectome.engine import atlas_paths, load_atlas
from neurographx.utils.paths import resolve


def main() -> int:
    cfg = load("data.yaml")
    vc, cc = cfg["verification"], cfg["connectome"]
    pipeline, strategy = cfg["pipeline"]["name"], cfg["pipeline"]["strategy"]
    ts_folder = resolve(cfg["paths"]["raw"]) / "ABIDE_pcp" / pipeline / strategy
    out_dir = resolve(cc["output_dir"])
    rng = np.random.default_rng(vc["seed"])

    per_atlas, detail = [], []
    for atlas in cfg["atlases"]:
        key = atlas["key"]
        npz, manifest = atlas_paths(out_dir, pipeline, strategy, key)
        if not npz.exists():
            print(f"{npz} missing. Run scripts/07_build_connectomes.py first.")
            return 1
        cset = load_atlas(npz, manifest, verify_hash=True)
        n = min(vc["participants_per_atlas"], len(cset))
        sample = list(rng.choice(len(cset), size=n, replace=False))
        with_flat = np.flatnonzero(cset.zero_var.any(axis=1))
        if len(with_flat) and not any(i in with_flat for i in sample):
            sample[-1] = int(rng.choice(with_flat))
        print(f"{atlas['label']}: checking {n} participants")

        results = []
        for i in sample:
            fid = str(cset.file_ids[i])
            ts = vf.read_1d_independent(ts_folder / f"{fid}_{key}.1D")
            res = vf.verify_one(cset.matrix(fid, "r"), cset.matrix(fid, "z"), cset.zero_var[i],
                                ts, cc["fisher_clip"], rng, vc["edges_for_scipy_check"])
            res.update({"atlas": atlas["label"], "FILE_ID": fid})
            results.append(res)
            detail.append(res)
        df = pd.DataFrame(results)
        per_atlas.append({
            "Atlas": atlas["label"], "Participants checked": n,
            "With flat regions": int((df.flat_regions > 0).sum()),
            "Max abs diff r, manual": f"{df.r_max_abs_diff_manual.max():.1e}",
            "Max abs diff r, scipy": f"{df.r_max_abs_diff_scipy.max():.1e}",
            "Max abs diff r, nilearn": f"{df.r_max_abs_diff_nilearn.max():.1e}",
            "Max abs diff z": f"{df.z_max_abs_diff.max():.1e}",
            "NaN pattern matches": f"{int(df.nan_pattern_match.sum())}/{n}",
            "Passed": f"{int(df.passed.sum())}/{n}",
        })

    summary = pd.DataFrame(per_atlas)
    all_ok = all(d["passed"] for d in detail)
    detail_df = pd.DataFrame(detail)[["atlas", "FILE_ID", "flat_regions",
                                      "r_max_abs_diff_manual", "z_max_abs_diff", "passed"]]
    text = "\n".join([
        "# Connectome Engine: Independent Verification",
        "",
        f"**Generated:** {dt.date.today().isoformat()}  ",
        f"**Sample:** {vc['participants_per_atlas']} participants per atlas, seed "
        f"{vc['seed']}, {vc['edges_for_scipy_check']} region pairs per participant for scipy  ",
        f"**Result:** {'ALL PASSED' if all_ok else 'FAILURES, investigate before training'}",
        "",
        "The engine (numpy loadtxt, corrcoef, arctanh) is compared with routes that share",
        "none of its code: pandas to read the file, the Pearson formula written out by hand,",
        "scipy.stats.pearsonr on sampled region pairs, nilearn ConnectivityMeasure with the",
        "empirical covariance, and the Fisher formula 0.5 ln((1 + r) / (1 - r)) written out.",
        "",
        f"Tolerance: absolute {vf.R_ATOL:g} for r; absolute {vf.Z_ATOL:g} plus relative "
        f"{vf.Z_RTOL:g} for z. Values are stored as float32, about seven significant digits.",
        "",
        "## Per atlas",
        "",
        summary.to_markdown(index=False),
        "",
        "## Every participant checked",
        "",
        detail_df.to_markdown(index=False, floatfmt=".1e"),
        "",
    ])
    path = resolve(vc["report"])
    path.write_text(text, encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"\nWrote {path}")
    print("ALL PASSED" if all_ok else "FAILURES FOUND")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
