# 0005. Frozen evaluation set

**Status:** Accepted
**Date:** 2026-09-28, drawn 2026-10-06
**Owner:** Aleesha Hayat

## Context

Every run in both semesters must be measured against the same held-out participants, or
results from different runs cannot be compared. If any evaluation participant is ever seen
during training, every number becomes meaningless. That failure is called data leakage.

## Decision

- **Size:** 100 participants.
- **Stratification:** by `SITE_ID` and `DX_GROUP` together, so the set is not dominated by
  a few hospitals or skewed toward one group.
- **Drawn once**, with the seed recorded in `configs/data.yaml`.
- **Committed** to the repository at `data/frozen/frozen_eval_100.csv` as a list of subject
  identifiers. It is the one thing under `data/` that is version controlled.
- **Never regenerated.**

## Enforcement

A pytest test asserts that no identifier in the frozen file appears in any training split.
It runs in CI on every push, so leakage fails the build rather than reaching a result.

## How it was drawn

In plain terms: the 861 QC-passing participants are grouped into 40 cells, one per
(site, diagnostic group) pair. Each cell gets a share of the 100 places in proportion to
its size. Shares are rounded with the largest remainder method so they add up to exactly
100. Within each cell, that many participants are picked at random with the recorded seed.

- Seed **20260928** (`configs/data.yaml`), numpy `default_rng`, cohort sorted by `SUB_ID`,
  cells visited in sorted order, so the draw is reproducible. A test re-draws it from the
  seed and checks it matches the committed file.
- Code: `neurographx.m1_ingestion.splits`, run once by `scripts/06_draw_frozen_set.py`,
  which refuses to overwrite an existing set.
- Sidecar `data/frozen/frozen_eval_100.meta.json` records the seed, method, full
  allocation table, and SHA-256 hashes of both the cohort file and the frozen file.
  A test fails if the frozen file is ever edited.

## Development pool and splits

Everyone else (761 participants) is the development pool. `data/splits/cv5_folds.csv`
assigns them to five folds, stratified the same way (seed 20261006). Any other training
split must be committed under `data/splits/`, where the leakage test finds it
automatically. A file with a `role` column is checked on its `train` and `val` rows; any
other file is checked in full.

## Confirmation (closed 2026-10-06)

- [x] Draw the set once the quality control screen has run, so it is drawn from retained
      participants only. Drawn from the 861 in `data/splits/qc_cohort.csv` (memo 0003).
- [x] Record the retained cohort size and the per-site composition here.
  Cohort 861 (396 autism, 465 control). Frozen set 100: **46 autism, 54 control,
  all 20 sites, all 40 site-by-group cells** (between 1 and 11 per cell; the expected
  share for every cell is within one participant). Full table in the meta file.
- [x] Commit the file and confirm the leakage test passes in CI.
  `tests/test_leakage.py` and `tests/test_frozen_set.py` pass locally; CI confirmation
  is recorded in `docs/progress/week-02/log.md` once the pull request is green.
