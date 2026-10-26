# Week 2 log

## Monday 5 October, stand-up
**Closed since last time:** Week 1 data work merged (PR #25): four atlases, 871 rater-passing participants.
**Next:** poster Monday and Tuesday; Aleesha's Week 2 build from Wednesday.
**Blocked:** nothing.

## Entries

### 6 October (Aleesha, started early)
- Memo 0003 closed: motion gate `func_mean_fd` at most 0.5 mm. QC cohort 861
  (396 autism, 465 control, 20 sites); 241 excluded by raters, 10 by motion, 0 by
  completeness. `scripts/05_apply_qc.py`, cohort and exclusion log committed.
- Connectome engine built (memo 0007): Pearson r, Fisher z, upper-triangle float32
  storage, fingerprint cache. All four atlases for 861 participants in about 33 s,
  cached re-run in about 6 s. Summary `docs/reports/connectome_summary.md`.
- Frozen evaluation set drawn once (memo 0005, seed 20260928): 100 participants,
  46 autism, 54 control, all 20 sites and all 40 site-by-group cells.
  Development pool of 761 in five stratified folds, `data/splits/cv5_folds.csv`.
- Leakage assertion: `tests/test_leakage.py` checks every split under `data/splits/`
  and proves the guard fires on a planted leak.
- Independent verification: 80 matrices (20 per atlas) recomputed by pandas, a
  hand-written Pearson formula, scipy and nilearn; all agree within float32 rounding.
  `docs/reports/connectome_verification.md`.
- Memo 0001 note: Dosenbach 160's 161st column is labelled `#223`; recorded, not explained.
- Fix: `tabulate` added to `requirements.txt`; the report scripts needed it but it was
  not pinned.
- Tests: 29 to 92, all passing locally with Python 3.11 on a clean copy without raw data.

### 10 to 11 October (Aleesha)
- Code review pass before publishing. Fixes:
  - `scripts/02_metadata_report.py` plotted `func_dvars` as "the" motion variable because
    it is the first motion-like column in the file. It now plots `func_mean_fd`, the
    variable the QC gate thresholds (`metadata.pick_motion_column`). Report regenerated.
  - `ConnectomeSet.edges` now rejects an unknown kind with a clear error.
  - `SETUP.md` no longer says "ten tests".
- Full pipeline rerun from scratch (`07 --force`): same matrices, verification all passed,
  frozen set and splits byte-identical (hash check before and after).
- Tests: 94 passing on a clean Python 3.11 copy without raw data, ruff clean.
- Branch `feature/m2-week2-connectome` created from `main` (091dcb7) and committed.
- First publish attempt stopped safely: main had 14 new commits (Laiba PRs #26 to #30,
  Alishba #31 and #32) and `requirements.txt` conflicted. Merged main into the branch:
  - `requirements.txt`: kept the API pins and added `tabulate`.
  - Connectome memo renumbered **0007** (Laiba's model architecture memo is 0006);
    it now states the interface agreed with 0006 (Fisher z rows as node features,
    z diagonal 0, thresholding in model code).
  - The API's participant screen (`screening.py`) now applies the closed motion gate.
    On the real phenotypic file it includes exactly the 861 of `qc_cohort.csv`;
    a test pins this agreement on synthetic data.
  - `ConnectomeSet` accepts the zero-padded ids the API and inference use ("0050003").
  - Tests: 138 passing, 2 skipped without PyTorch (same as CI).
  Published with `docs/progress/week-02/publish_week2.sh`: sync with GitHub, local
  tests, push, pull request, wait for CI, merge.

### Handoff to Laiba
- Load matrices with `load_atlas` (example in memo 0007). Use `fill_nan=0.0` for now and
  confirm or amend the flat-region proposal in memo 0007 before training.
- Train only on `data/splits/cv5_folds.csv` or another file committed under
  `data/splits/`. Evaluate once on `data/frozen/frozen_eval_100.csv`.
- Call `assert_no_leakage(train_ids, frozen)` from
  `neurographx.m1_ingestion.splits` before fitting.

## Thursday 8 October, stand-up
**Closed since last time:**
**Next:**
**Blocked:**

## Decisions taken
- `docs/decisions/0003-qc-criteria.md` (closed 6 October)
- `docs/decisions/0005-frozen-evaluation-set.md` (accepted 6 October)
- `docs/decisions/0007-connectome-engine.md` (new)

## Week close, Sunday 11 October
**Gate items met:**
**Gate items missed, and why:**
**Carried into next week:**
**CI run for the Week 2 pull request:** (paste the Actions link once green)
**Board screenshot:** `board.png`
