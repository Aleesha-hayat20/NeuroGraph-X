# Week 1 log

## Monday 28 September, stand-up
**Closed since last time:** project kickoff, nothing prior.
**Next:** repository creation, phenotypic download, environment verification, board setup.
**Blocked:** nothing.

## Entries

### 29 September
- Repository scaffold created: package layout, pinned requirements, pytest, GitHub Actions.
- Decision memos drafted: 0001 atlas selection (accepted), 0002 pipeline and strategy
  (proposed), 0003 quality control criteria (accepted), 0004 node count handling
  (accepted), 0005 frozen evaluation set (proposed).
- Quality control rater column names confirmed against `nilearn.datasets.fetch_abide_pcp`
  source, version 0.14.1: `qc_rater_1`, `qc_anat_rater_2`, `qc_func_rater_2`,
  `qc_anat_rater_3`, `qc_func_rater_3`.
- Confirmed the derivative extension rule: `rois_*` derivatives are `.1D` text files,
  everything else is `.nii.gz`.

### 01 October
- Fix 01: strategy parsing bug caught during verification and fixed before
  script 03 was ever run. "filt" is a substring of "nofilt", so the two
  nofilt strategies would have fetched the wrong preprocessing variant.
  Configured strategy filt_global was unaffected. Tests up from 10 to 18.
- Metadata report generated: `docs/reports/metadata_report.md` plus figures.
- Decision memo 0002 accepted: `cpac` / `filt_global` matches the preprocessing of the
  primary comparator, Heinsfeld et al. 2018.
- Pilot atlas run (CC200, 5 participants): `scripts/03_pilot_atlas.py`. 
  Result: Pilot passed. Safe to run scripts/04_fetch_all_atlases.py 
  Figure: `docs/reports/figures/pilot_connectivity_matrix.png`.
- Full four atlas download (2 October): `scripts/04_fetch_all_atlases.py`. 871 participants
  passed quality control (403 autism, 468 control, 20 sites), the same set in all four
  atlases. Region counts: AAL 116, CC200 200, Harvard-Oxford 111, Dosenbach 160 161.
  0 invalid matrices. 992.1 MB on disk. Summary in `docs/reports/atlas_summary.md`.
  Memo 0001 closed.

### Handoff to Laiba
- Region time series for all four atlases sit in `data/raw/ABIDE_pcp/cpac/filt_global/`
  on Aleesha's machine (not committed, too large and regenerable). Re-create with
  `python scripts/04_fetch_all_atlases.py`.
- Node counts per atlas are in `docs/reports/atlas_summary.md`; one model per atlas (0004).
- Correlation code: `neurographx.m2_connectome.connectivity`. Regions with a flat signal
  give empty (NaN) rows; how to treat them needs its own short memo before training.

## Decisions taken
- `docs/decisions/0002-pipeline-strategy.md` (accepted 1 October)
- `docs/decisions/0003-qc-criteria.md`
- `docs/decisions/0004-node-count-handling.md`

## Week close, Sunday 4 October
**Gate items met:**
**Gate items missed, and why:**
**Carried into next week:**
**Board screenshot:** `board.png`
