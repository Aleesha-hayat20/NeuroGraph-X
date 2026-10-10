## What this adds

- **QC closed (memo 0003):** mean framewise displacement at most 0.5 mm. Cohort of 861 (396 autism, 465 control, 20 sites); exclusion log with every reason.
- **Connectome engine (memo 0007):** Pearson r and Fisher z for AAL, CC200, Harvard-Oxford and Dosenbach 160; upper-triangle float32 storage; fingerprint cache.
- **Frozen evaluation set (memo 0005):** 100 participants stratified by site and group together, seed 20260928, committed with hashes; never regenerated.
- **Leakage assertion:** `tests/test_leakage.py` checks every split under `data/splits/` and proves the guard fires on a planted leak.
- **Independent verification:** 80 matrices recomputed with pandas, a hand-written Pearson formula, scipy and nilearn; all agree within float32 rounding.
- **Fixes:** `tabulate` pinned in requirements; the metadata report's motion figure now shows `func_mean_fd` (the QC variable) instead of `func_dvars`.

## For Laiba

Train only on `data/splits/cv5_folds.csv` (or a split committed under `data/splits/`). Evaluate once on `data/frozen/frozen_eval_100.csv`. Please confirm the flat-region proposal in memo 0007.

## Checks

- ruff clean, 94 tests pass on a clean Python 3.11 copy without raw data
- CI on this PR must be green before merging
