#!/usr/bin/env python3
"""Week 2, step 5: apply the quality control screen fixed in decision memo 0003.

Usage:
    python scripts/05_apply_qc.py

Reads the phenotypic CSV and the region time series downloaded in Week 1, applies
the rater, motion and completeness gates, and writes:

    data/splits/qc_cohort.csv          the retained cohort, committed
    docs/reports/exclusion_log.csv     every excluded participant with the reason, committed

Run it before 06_draw_frozen_set.py. The frozen set is drawn from this cohort only.
"""

from __future__ import annotations

import sys

from neurographx.config import load
from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion.qc import apply_qc, gate_counts
from neurographx.utils.paths import resolve


def main() -> int:
    cfg = load("data.yaml")
    qc_cfg = load("qc_criteria.yaml")
    raw = resolve(cfg["paths"]["raw"])
    csv_path = raw / cfg["dataset"]["phenotypic_file"]
    folder = raw / "ABIDE_pcp" / cfg["pipeline"]["name"] / cfg["pipeline"]["strategy"]
    if not csv_path.exists() or not folder.exists():
        print("Phenotypic file or time series folder missing. Run scripts 01 and 04 first.")
        return 1

    df = md.load_phenotypic(csv_path)
    atlas_keys = [a["key"] for a in cfg["atlases"]]
    retained, log = apply_qc(df, qc_cfg, folder, atlas_keys)

    cohort_path = resolve(cfg["cohort"]["file"])
    log_path = resolve(cfg["cohort"]["exclusion_log"])
    cohort_path.parent.mkdir(parents=True, exist_ok=True)
    retained.to_csv(cohort_path, index=False, lineterminator="\n")
    log.to_csv(log_path, index=False, lineterminator="\n")

    c = gate_counts(log, len(df))
    print(f"Participants in phenotypic file ..... {c['total']}")
    print(f"Excluded at rater gate .............. {c['excluded_rater']}")
    print(f"Excluded at motion gate ............. {c['excluded_motion']}"
          f"  ({qc_cfg['motion']['column']} > {qc_cfg['motion']['mean_fd_max']} mm)")
    print(f"Excluded at completeness gate ....... {c['excluded_completeness']}")
    print(f"Retained ............................ {c['retained']}")
    groups = retained["DX_GROUP"].map(md.DX_LABELS).value_counts().to_dict()
    print(f"Retained by group ................... {groups}")
    print(f"Sites represented ................... {retained['SITE_ID'].nunique()}")
    print(f"\nWrote {cohort_path}\nWrote {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
