# 0009. Serving checkpoints: where they live, how they are found, CPU inference

**Status:** Accepted on 12 November 2026, option A. Held open at the Week 5 Thursday
stand-up until the ABIDE data terms were checked; see Acceptance at the end.
**Date:** 2026-10-31
**Owner:** Laiba Afridi
**Related:** 0004 (one model per atlas), 0005 (frozen set), 0006 (model architecture),
0008 (database schema), 0011 (tuning protocol), 0013 (analysis log and API contract),
0014 (fixture data)

## Context

Models are trained on Kaggle's GPU and served by the API on an ordinary laptop. Until now
the only real checkpoint, `checkpoints/cc200_00252f2b.pt`, existed on Kaggle and on two
laptops, because `.gitignore` excludes every `*.pt` file. Three things now depend on
checkpoints being findable and reproducible on any machine:

1. **The demo and `POST /analyses`** (memo 0013) load the registered model for an atlas.
2. **Regenerate** (memo 0013, part 3) re-runs an old analysis with **the original run's
   checkpoint**, which may no longer be the registered one.
3. **Fixture mode** (memo 0014) needs the registry's relative checkpoint path resolved
   against `fixtures/`, not the working directory. Until now its test changed directory to
   work around this.

Facts this memo relies on:

- A checkpoint is small. The CC200 model has 25,474 parameters (memo 0006), about
  100 KB of weights; the other three atlases are smaller.
- Each checkpoint stores its weights plus everything needed to rebuild the model and the
  graph: `in_dim`, `hidden`, `layers`, `dropout`, `num_classes`, `atlas`, `atlas_key`,
  `density`, `fill_nan`, `run_id` (written by `scripts/train_gnn.py`, stage `final`).
  `model_from_checkpoint` rebuilds the architecture from these sizes before loading the
  weights, so a checkpoint cannot be loaded into the wrong shape.
- Inference loads with `map_location="cpu"` and switches the model to `eval()` (dropout
  off). No GPU is needed to serve.

## Decision

### 1. Naming and immutability

- One file per final run: `checkpoints/<atlas>_<run_id>.pt`, written only by
  `train_gnn.py --stage final`. Cross-validation saves no checkpoint.
- A checkpoint is never overwritten or renamed. A new model is a new run with a new
  `run_id`; the registry moves to it and keeps the old one under `previous_run_ids`.

### 2. How a checkpoint is found

- The registry and run log store a **relative** path (`checkpoints/cc200_00252f2b.pt`).
- `inference.checkpoint_path(entry, registry_path)` resolves it against the data root that
  holds the registry: a registry in `<root>/runs/` means `<root>/checkpoints/`, through
  `datasource.checkpoint()`. The real registry resolves to the repository root, the fixture
  registry to `fixtures/`, from any working directory.
- `load_model` uses it, so the API, the CLI and the tests all find checkpoints the same way.
  A registry kept anywhere else keeps the old behaviour (relative to the working directory),
  so no existing caller changes. Implemented in this week's pull request, with a test.

### 3. Where checkpoints are kept (to decide at the stand-up)

| Option | For | Against |
|---|---|---|
| **A. Commit the checkpoints of final runs** (a `.gitignore` exception `!checkpoints/*_<run_id>.pt` per run, as memo 0014 did for the fixture) | A clean clone can serve and regenerate offline; files are about 100 KB each; history keeps every model regenerate may need | Binary files in git; needs a check that ABIDE's data-sharing terms allow sharing trained weights |
| B. Attach them to a GitHub release | Repository stays text-only | A second download step; regenerate breaks if the release is edited |
| C. Shared drive, as now | No change | Not reproducible from the repository; the demo depends on one laptop |

**Proposed: A**, for final runs only (at most four registered models plus any declared CC200
repeat under memo 0011), **once Aleesha confirms the ABIDE terms allow it.** Until then, C
continues and the checkpoint is copied by hand to the demo machine.

### 4. CPU inference is the reference for serving

- `scripts/predict_one.py --participant <id> --atlas <atlas> --expect <prediction>:<confidence>`
  runs one prediction on the CPU through the registry and compares it with a reference.
  It reads no labels and writes nothing, so it is not a frozen-set measurement.
- The CC200 reference is the Kaggle GPU output of run `00252f2b` (12 October 2026,
  `docs/progress/week-02/week-02-inference.jpeg`): participant `0050011`, `control`,
  confidence 0.7052. A CPU result **matches** when the prediction is the same and the
  confidence is within 0.001: CPU and GPU kernels differ in the last decimals, not more.
- The same script runs on the fixture data with `NGX_DATA=fixtures`, so the CPU path can be
  checked on a machine without the real connectomes.

### 5. Integrity (Week 5, with the schema change of memo 0011)

The run log records the SHA-256 of each checkpoint it writes (new field
`checkpoint_sha256`), and `load_model` refuses a checkpoint whose hash differs. This is a
new run-log field, so it goes in the same `schema_version` 3 change as memo 0011's
`repeat_reason` (Alishba: `db/schema.sql`, `RUN_LOG_COLUMNS`, ER diagram).

## Rationale

- **Relative paths resolved against the data root** keep the registry portable between
  Kaggle, the Mac, Windows and CI, and make fixture mode work without changing directory.
- **Immutable, run-named files** are what makes regenerate possible: the run id in an
  analysis record always names exactly one file.
- **CPU as the serving reference** matches where the API runs. Training stays on the GPU.
- **Option A** is small, offline and reproducible; the only open point is permission.

## Consequences

- `inference.py` gains `checkpoint_path`; `load_model` uses it. Existing callers and tests
  are unchanged (all pass); a new test loads a checkpoint through a registry in
  `<root>/runs/` from another working directory.
- `tests/test_fixture_data.py` no longer needs to change directory to `fixtures/`; the
  workaround can be removed in a later clean-up (Aleesha), it does no harm meanwhile.
- `POST /analyses` (Week 5) calls `inference.predict` with the active data mode's registry,
  `datasource.model_registry()`, and gets fixture or real checkpoints with no extra code.
- If option A is accepted: `.gitignore` exceptions and the CC200 checkpoint in one pull
  request, after the ABIDE terms are confirmed.

## To confirm

- [x] `predict_one.py` on the Mac with the CC200 checkpoint matches the reference
  (`control`, 0.7052 within 0.001): matched on 6 November (Week 5 log).
- [x] Aleesha: ABIDE's terms allow committing trained weights (option A): yes, see below.
- [x] Option A chosen, on 12 November 2026.
- [x] `checkpoint_sha256` added with memo 0011's `schema_version` 3 change (PR #94).

## Acceptance (12 November 2026)

- **Option A.** The checkpoints of the final runs are committed under `checkpoints/`, with
  one `.gitignore` exception per file, so no other checkpoint is committed by accident.
  This covers the four registered models and the archived CC200 run `00252f2b`, whose
  frozen-set result is reported alongside the declared repeat (memo 0011), so that every
  reported model can be loaded and regenerated from a clean clone. Each file's SHA-256 is
  the one its run recorded in `runs/run_log.jsonl`. Training checkpoints that are not final
  stay out of git.
- **Licence.** ABIDE I states that data usage is unrestricted for non-commercial research,
  under a Creative Commons Attribution-NonCommercial-ShareAlike licence
  ([ABIDE I page](https://fcon_1000.projects.nitrc.org/indi/abide/abide_I.html)). The
  weights are derived from that data, as preprocessed by the Preprocessed Connectomes
  Project, so `checkpoints/README.md` states that they are shared on the same terms
  (CC BY-NC-SA 3.0, non-commercial research and teaching use, with attribution to ABIDE I
  and the Preprocessed Connectomes Project) and are not a diagnostic or medical device.
- **Checked by** `scripts/check_integrity.py`: every registered and archived checkpoint is
  present and matches its logged SHA-256 (or, for `00252f2b`, which predates schema 3, is
  reported as recorded without a hash).
