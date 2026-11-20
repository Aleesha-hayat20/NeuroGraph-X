# 0016. Reliability engine skeleton

**Status:** Proposed in Week 7 (17 November 2026). Implemented on
`feature/week7-reliability-tests`.
**Date:** 2026-11-17
**Owner:** Aleesha Hayat
**Related:** 0001 (atlases), 0005 (frozen set), 0008 (database schema), 0011 (tuning and the
frozen set), 0014 (fixture data), 0015 (real-world repositioning, Section 4.3)

## Context

Work plan Section 10, item 6, asks for the skeleton of the reliability module (M5) in
FYP-I: a job manifest whose jobs carry an axis, a value, an atlas and a seed, and a
resumable runner that writes each variant run to the run log with `stage: "variant"`,
tested on a small synthetic grid.

The supervisor has directed that the reliability finding on ABIDE is delivered in FYP-II,
so no ABIDE reliability result is produced or presented in FYP-I. Memo 0015 (Section 4.3)
makes that finding the trust information shown with every result in FYP-II, with the
leave-site-out accuracy as the expected performance on a scanner the model never saw.

**In plain words:** a reliability study asks how much a result moves when one thing about
the training changes. Each re-run with one change is a *variant*. The *axis* is the thing
that changes (atlas, seed, training sample or site), and the *value* is what it is changed
to. A *job* is one variant to run; a *grid* is the set of jobs, and its *manifest* is the
written list of every job.

## Decision

### 1. Four axes, one change per job

| Axis | Value | Training and evaluation |
|---|---|---|
| `atlas` | the atlas key | The reference run of that atlas: the five CV folds of `cv5_folds.csv`, the base seed |
| `seed` | a seed | The same five folds; only the random seed of training changes |
| `resample` | 0, 1, 2, ... | One stratified bootstrap of the development pool (drawn with replacement, the same number of participants per diagnosis as the pool), evaluated on the participants it did not draw ("out of bag") |
| `site` | a site | Every other site trains; the named site is evaluated |

Every job is run once per atlas in the grid, so a job always names its atlas. A bootstrap is
fixed by its seed and index, so the same job draws the same sample on every machine.

All splits come from the development pool. The frozen evaluation set (memo 0005) is read
for its participant IDs only, to check before any training that it shares no participant
with the pool; it is never scored. The frozen-set protocol of memo 0011 is unchanged.

### 2. A fixed number of epochs

Every variant trains for exactly the configured number of epochs. The CV stage of
`train_gnn.py` keeps the best epoch on each validation fold, which is a choice made on the
participants it then scores. A variant must not do that: its score is the measurement the
module reports, so nothing in it is tuned to the participants it is scored on. As a result
a reference run is not the same number as a tuning run of memo 0011; variants are compared
with each other, under one fixed recipe.

### 3. Grid definition and manifest

A grid is defined in YAML under `configs/reliability/`: its name, the atlases, the base
seed, the axes and the model settings. `scripts/run_reliability.py` expands it into a
manifest, written once to `runs/reliability/<name>/manifest.json` in the output folder.

- The manifest identifier is a hash of the definition. Each job identifier is a hash of the
  manifest identifier and the job's axis, value, atlas and seed. The same definition
  always gives the same identifiers; any change gives new ones.
- A manifest is never replaced. A different definition under an existing name is refused,
  because the runs already logged would no longer match it. A changed grid gets a new name.
- A definition that repeats a job, names an unknown axis or a site outside the development
  pool, or lacks a model setting is refused before anything runs.

### 4. Run-log record

One record per finished job, appended by `run_logger.log_run`:

- `stage: "variant"`, `dataset` (`synthetic_fixture` or `ABIDE`), `atlas`, `seed`, the
  hyperparameters, and a `data_config` with the hashes of the folds file, the frozen file
  and the connectome store;
- `metrics`: the pooled score over every evaluated participant, the score of each split
  (accuracy, balanced accuracy, AUC, majority-class baseline, confusion matrix) and the
  per-participant prediction file with its SHA-256
  (`runs/reliability/<name>/<job_id>.csv`);
- `reliability`: the grid name, the manifest identifier, the job identifier, the axis and
  the value;
- `checkpoint_path: "none (reliability variant)"`. Variants are measurements, not models to
  serve, so no checkpoint is saved.

`db/schema.sql` accepts `variant` in the `stage` check and adds a `reliability` column
(JSON text). The record schema version stays 3: no existing record changes meaning, the new
field appears only on the new stage, and the fixture's committed run log stays valid.

### 5. Resuming

A job is done when the run log holds a `variant` record with its manifest identifier and
job identifier. The runner writes a record only after its job has finished, so a run that
stops loses at most the job in progress, and the same command again runs only the jobs
still pending. `--max-jobs` stops after a set number of jobs and `--dry-run` lists the
pending jobs without training or writing anything.

### 6. Guards

- Real ABIDE data is refused unless `--allow-real-data` is given. In fixture mode the runner
  also refuses a development pool whose sites are not the fixture's synthetic sites.
- The output folder must lie outside `fixtures/`, whose files are hash-checked (memo 0014).
- The leakage check of memo 0005 runs before the first job.

### 7. FYP-I scope

The FYP-I grid is `configs/reliability/fixture_grid.yaml`: the two fixture atlases (CC200
and Harvard-Oxford), the reference run, two seeds, two bootstraps and each of the three
synthetic sites left out, 16 jobs in all. `tests/test_reliability.py` runs it with a
stand-in trainer to check the manifest, the splits, resuming and the guards, and trains the
real GCN on one job twice to check that the same job gives the same predictions. Nothing
measured on the fixture is a result (memo 0014).

## Consequences

- FYP-II adds an ABIDE grid definition and runs it with `--allow-real-data`. The development
  pool holds 761 participants from 20 sites, the smallest with 9, so a leave-site-out score
  on a small site is coarse and is reported with its number of participants.
- How the variants are summarised into the reliability envelope (the spread statistic,
  and how the site scores are combined) is decided in FYP-II, before the ABIDE grid runs,
  so the summary is not chosen after seeing the results.
- Tuning, calibration, the registry, the model cards and the integrity check pick runs by
  stage (`cv` or `final`) or by run identifier, so variant records do not enter them.
- `scripts/import_results.py` brings Kaggle runs into the repository. When the ABIDE grid
  runs on Kaggle, it also needs to copy `runs/reliability/` and check each prediction file
  against the SHA-256 in its record (FYP-II).
- The ER diagram (`docs/design/database_schema.puml` and its PNG) shows the new column.

## Open items

- [ ] Summary of the reliability envelope, before the ABIDE grid runs (FYP-II).
- [ ] Whether the explanation module (M4) needs variant checkpoints. If it does, this memo
      is amended to save them.
