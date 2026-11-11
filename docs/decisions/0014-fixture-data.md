# 0014. Fixture dataset and fixture mode

**Status:** Accepted at the Week 5 Thursday stand-up (29 October 2026); amended
2026-10-27 (completeness case) and 2026-11-06 (run-log schema 3; see Amendments).
Implemented on `feature/week4-fixtures-memos`.
**Date:** 2026-10-24
**Owner:** Aleesha Hayat
**Related:** 0001 (atlases), 0003 (QC), 0005 (frozen set), 0007 (connectome engine),
0008 (database schema), 0009 (serving checkpoints), 0012 (dashboard), 0013 (API contract)

## Context

The real data is about 1 GB and is not committed: the phenotypic table and time series sit
in `data/raw/`, the connectomes in `data/processed/`, and trained checkpoints on Kaggle and
the team's laptops. So nothing that runs on a clean machine can reach it: not GitHub
Actions, not Alishba's dashboard while the backend is still being built, not the Week 6
end-to-end test, and not a teammate following `SETUP.md` from a fresh clone.

The work plan (Section 5.5) asks for one environment setting that points the API at a
small stand-in dataset instead.

**In plain words:** a *fixture* is a small, fake, fixed dataset kept with the code so
that tests and demos of the *software* can run anywhere. It is not used for any research
result. This matters because the project avoids synthetic data for results: nothing
measured on the fixture is ever reported, and the fixture's README says so.

## Decision

### 1. What the fixture contains

Everything lives under `fixtures/`, in the same layout as the repository, so switching
datasets only changes the root folder.

| File under `fixtures/` | Real counterpart | Contents |
|---|---|---|
| `data/raw/Phenotypic_V1_0b_preprocessed1.csv` | same path | 24 invented participants, 3 invented sites (`SYN_A`, `SYN_B`, `SYN_C`), the **106 real columns in the real order** |
| `data/splits/qc_cohort.csv`, `docs/reports/exclusion_log.csv` | same paths | 17 retained, 7 excluded (rater 4, motion 2, completeness 1) |
| `data/frozen/frozen_eval_6.csv` + `.meta.json` | `frozen_eval_100.*` | 6 participants, one per (site, group) cell |
| `data/splits/cv5_folds.csv` | same path | development pool of 11 in 5 folds |
| `data/processed/connectomes/cpac_filt_global/rois_cc200.npz/.json`, `rois_ho.npz/.json` | same paths | two atlases at their real sizes, 200 and 111 regions |
| `runs/run_log.jsonl`, `runs/model_registry.json` | same paths | one cross-validation run and one final run; CC200 registered |
| `checkpoints/cc200_<run_id>.pt` | `checkpoints/cc200_00252f2b.pt` | a tiny GCN (2 layers, 8 hidden units, 1,770 parameters, about 11 KB) |
| `configs/data.yaml` | `configs/data.yaml` | the real file with only the frozen-set size and file names changed |
| `README.md`, `MANIFEST.json` | none | a SYNTHETIC banner; the hash of every file |

Total size about 3.8 MB, almost all of it the CC200 connectome file.

### 2. Only the inputs are invented

The generator (`src/neurographx/fixture_data.py`, run by `scripts/build_fixtures.py`)
invents two things: the phenotypic rows and the region time series. Every other file is
written by the **same project code** that wrote the real one:

| Output | Written by |
|---|---|
| QC cohort and exclusion log | `m1_ingestion.qc.apply_qc`, with the **real** `configs/qc_criteria.yaml` |
| Frozen set, its sidecar, CV folds | `m1_ingestion.splits` (`stratified_draw`, `write_frozen`, `make_folds`) |
| Connectome `.npz` and manifest | `m2_connectome.engine.build_atlas` |
| Run log and registry | `m3_model.run_logger` (`log_run`, `register_model`) |
| Checkpoint | `m3_model.model.GCN`, saved with the same keys as `scripts/train_gnn.py` |

So if a real format changes, the fixture changes with it on the next regeneration, and
the tests below notice until it is regenerated.

### 3. Fixture mode: one setting, `NGX_DATA`

| Value | Effect |
|---|---|
| unset, empty or `real` | real data under the repository root (unchanged behaviour) |
| `fixtures` | every read goes to `fixtures/` |
| anything else | an error at start-up that names the allowed values, never a silent guess |

`src/neurographx/datasource.py` is the one place that answers "where is file X for the
active dataset": `phenotypic_table()`, `qc_cohort()`, `exclusion_log()`, `frozen_set()`,
`cv_folds()`, `connectome_dir()`, `run_log()`, `model_registry()`, `analysis_log()` and
`checkpoint(path)`. The API's participant table already goes through it, and `/health`
now reports `data_mode`, so the dashboard can show a "fixture data" banner.

Two limits, on purpose:

- **Only the reading side switches.** The numbered pipeline scripts and
  `scripts/train_gnn.py` always use the real data, so a shell left with
  `NGX_DATA=fixtures` can never overwrite real outputs.
- **QC rules are never copied.** The fixture is screened with the real
  `configs/qc_criteria.yaml`; it carries no rules of its own.

How to use it:

```bash
NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app --reload   # or: make api-fixtures
python scripts/smoke_api.py --data fixtures                             # or: make smoke
```

### 4. Planted cases

Each rule of memo 0003, and each edge of each rule, appears at least once.

| SUB_ID | Case | Expected outcome |
|---|---|---|
| 90007 | `FILE_ID` is `no_filename`; three raters fail (like ABIDE 50002) | excluded, rater |
| 90008 | `qc_func_rater_2` fail | excluded, rater |
| 90015 | `qc_anat_rater_3` fail | excluded, rater |
| 90016 | `func_mean_fd` 0.62 | excluded, motion |
| 90023 | `func_mean_fd` missing | excluded, motion |
| 90024 | `qc_rater_1` "maybe" and `func_mean_fd` 0.71 | excluded, two gates (`rater;motion`) |
| 90012 | passes raters and motion, but its Dosenbach 160 time series file is never written | excluded, completeness ("missing rois_dosenbach160 file") |
| 90002, 90003 | "maybe" from rater 2 | retained ("maybe" is accepted there) |
| 90010 | `func_mean_fd` exactly 0.5 | retained (the limit is "at most 0.5 mm") |
| 90011 | one flat CC200 region | retained; NaN row on disk, filled with 0 for the model |
| 90005, 90020 | flat Harvard-Oxford regions (3 and 1) | retained; as above |

And one of each atlas state the API must handle: CC200 has data and a model; Harvard-Oxford
has data but **no model** (the 503 "no model registered" path); AAL and Dosenbach 160 have
**no stored connectomes** (the 503 "data unavailable" path).

SUB_IDs start at 90001. The 1,112 SUB_IDs in the real phenotypic file run from 50002 to
51607, so a fixture participant can never be mistaken for a real one, and a test checks
the two sets do not meet.

### 5. What the tests guarantee (`tests/test_fixture_data.py`, `tests/test_datasource.py`)

1. **Untouched:** every fixture file matches `MANIFEST.json`.
2. **Reproducible:** the generator rebuilds identical CSVs and identical connectome inputs
   (the engine's input fingerprint matches) from its seed.
3. **Real formats:** the phenotypic header equals the 106 columns listed in
   `docs/reports/metadata_report.md`; the connectome files have the arrays, types and
   manifest keys today's engine writes; the run log and registry import into
   `db/schema.sql`; the fixture config differs from the real one only in the declared keys.
4. **Real rules:** re-running memo 0003's screen on the fixture table reproduces its cohort
   and exclusion log; re-drawing the frozen set and folds from their seeds reproduces them;
   no leakage.
5. **Consistent:** the registry points at logged runs and an existing checkpoint; the
   hashes recorded in each run match the folds, frozen and connectome files (the Week 6
   integrity check in miniature); reloading the checkpoint reproduces the recorded
   frozen-set confusion matrix; the model predicts both classes across the cohort.
6. **The API runs on it:** `/health`, `/participants` and `/participants/{id}` in fixture
   mode, through FastAPI's test client in pytest, and through a real uvicorn process in
   `scripts/smoke_api.py`, which CI runs on every push.

### 6. Regenerating

Regenerate when a real format changes (a new run-log field, an engine version, a schema
change), or when the generator itself changes:

```bash
python scripts/build_fixtures.py --force
pytest tests/test_fixture_data.py tests/test_datasource.py
```

Commit the regenerated `fixtures/` in the **same pull request** as the code change that
needed it. Never edit a fixture file by hand; the manifest test fails if anyone does. The
generator refuses to delete a folder that has no `MANIFEST.json`, so a mistyped `--out`
cannot wipe anything else.

## Rationale

- **Invent inputs, not outputs.** Hand-written outputs would drift from what the code really
  writes, and a test passing on them would prove little. Running the real code over
  invented inputs makes the fixture a by-product of the pipeline itself.
- **The full 106-column header.** Several modules read columns by name. A fixture with only
  the columns we use today would hide the case where someone starts reading a new one.
- **Real atlas sizes.** The model's input size is the region count (memo 0004), and the
  dashboard shows it. A 10-region toy would test a different shape from the one served.
- **CC200 and Harvard-Oxford.** CC200 is the atlas with a registered real model.
  Harvard-Oxford has by far the most participants with flat regions in the real cohort
  (198 of 861, memo 0007), so it exercises the NaN path.
- **A trained tiny model, not random weights.** The registry, run log and checkpoint then
  form the same chain as the real ones, and predictions differ between participants.
  One deviation from `scripts/train_gnn.py`: the final fixture model trains for the full
  60 declared epochs instead of the median best epoch from cross-validation, because on
  validation folds of two or three participants that number is noise, and an under-trained
  model gives confidences so close to 0.5 that another CPU could flip a prediction.
- **Committed, not generated in CI.** A clean clone works offline, CI does not need to
  train anything, and the manifest makes any accidental edit visible in review.
- **An environment variable, not a command-line flag.** The same setting works for uvicorn,
  pytest, CI and the dashboard's development server without changing any of them.

## Consequences

- About 3.8 MB of binary files enter git history. Regenerate only when a format changes.
- The fixture checkpoint is the first `.pt` file in the repository (a `.gitignore`
  exception for `fixtures/checkpoints/*.pt`). Whether the four real checkpoints are
  committed is memo 0009's decision, not this one.
- `m3_model.inference.load_model` opens the registry's checkpoint path relative to the
  working directory. That works for the real registry when the API is started from the
  repository root, but in fixture mode it must go through `datasource.checkpoint()`.
  Today's fixture test changes directory to `fixtures/` to work around it. **Open item for
  Laiba (memo 0009, Week 5):** resolve checkpoint paths with `datasource.checkpoint()` in
  the `POST /analyses` path.
- Since memo 0013 the API reads participant status from the committed QC outputs, which
  include the completeness gate, so the fixture now plants a completeness case (90012; see
  Amendments). The real run excluded nobody at that gate.
- Analyses run in fixture mode are written to `fixtures/runs/analysis_log.jsonl`, which is
  ignored by git and excluded from the manifest.
- No accuracy, confidence or calibration figure measured on the fixture may appear in the
  report, the deck or the README.

## To confirm

- [x] CI is green with the new smoke step on the Week 4 pull request (PR #87).
- [x] Alishba runs the dashboard against `make api-fixtures` (memo 0012; evidence in
  `docs/progress/week-05/react-check/`).
- [x] Laiba resolves checkpoints through `datasource.checkpoint()` in `POST /analyses`
  (memo 0009; through `api/analysis_checks.py`, PR #126).
- [x] Accepted at the Week 5 Thursday stand-up (29 October).

## Amendments

### 2026-10-27: a completeness case (generator 1.1.0)

- Participant 90012 passes the rater and motion gates, but the generator never writes its
  Dosenbach 160 time series file, so the real QC code excludes it at the completeness gate
  (memo 0003, gate 3). Every gate is now planted at least once.
- Counts change: 17 retained and 7 excluded (rater 4, motion 2, completeness 1); frozen set
  still 6 (one per site and group cell); development pool 11. Regenerated with
  `python scripts/build_fixtures.py --force`.
- `runs/neurographx.sqlite` (written by `python scripts/build_db.py --data fixtures`) is a
  runtime file like the analysis log: ignored by git and left out of the manifest.

### 2026-11-06: run-log schema 3 and prediction files (generator 1.2.0)

- Laiba's PRs #93 and #94 changed two real formats: the run log moved to schema 3
  (`repeat_reason`, `checkpoint_sha256`; memos 0009 and 0011), and training now writes
  out-of-fold probabilities (`runs/oof/`) for cross-validation runs and frozen-set
  probabilities (`runs/frozen_predictions/`) for final runs (memo 0010). Section 6 of this
  memo says the fixture follows any real format change, so the generator now writes all
  four with the same code (`m3_model.run_logger`, `m3_model.oof`), and the regenerated
  fixture was committed with it.
- New tests: the fixture's runs carry the current schema version; the final run's
  `checkpoint_sha256` matches its file and `load_model` refuses a changed copy; the
  out-of-fold and frozen prediction files pass `check_oof` and match their recorded hashes.
- The working-directory workaround is gone from the tests: since memo 0009,
  `load_model` resolves checkpoints against the data root.
- Participants, splits and connectomes are unchanged from 1.1.0 (17 retained, 7 excluded);
  only the model files, run IDs and the new prediction files differ.
