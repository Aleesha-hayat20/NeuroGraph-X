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

### DD September
-

## Decisions taken
- `docs/decisions/0001-atlas-selection.md`
- `docs/decisions/0003-qc-criteria.md`
- `docs/decisions/0004-node-count-handling.md`

## Week close, Sunday 4 October
**Gate items met:**
**Gate items missed, and why:**
**Carried into next week:**
**Board screenshot:** `board.png`
