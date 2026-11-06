# Week 4 log

## Monday 19 October, stand-up
**Closed since last time:** (fill in)
**Next:** midterm freeze and rehearsal Monday and Tuesday; defence Wednesday.
**Blocked:** nothing

## Thursday 22 October, stand-up
**Closed since last time:** midterm defended on Wednesday 21 October.
**Jury comments turned into issues:** currently pending
**Next:** production track, tasks in `plan.md`.
**Blocked:** nothing

## Entries

### 24 to 25 October (Aleesha)
- Repository state checked before starting: `main` at `c419421` (PR #38, torch and
  torch-geometric pinned in `requirements.txt`), after PRs #34 and #35 (CC200 baseline:
  CV accuracy 0.6728, frozen set measured once, 0.63 against a 0.54 majority baseline).
  Suite: 157 passing with PyTorch installed.
- **Fixture dataset (memo 0014).** `scripts/build_fixtures.py` writes `fixtures/`: 24
  synthetic participants in the 106-column phenotypic format; QC cohort 18, excluded 6,
  every gate and rule edge planted; frozen set 6; 12 in 5 folds; CC200 and Harvard-Oxford
  connectomes at their real sizes; a tiny registered CC200 model (1,770 parameters).
  Only the inputs are invented; every output is written by the project's own QC, splits,
  engine and run-logger code.
- **Fixture mode.** One setting, `NGX_DATA=fixtures`, through
  `src/neurographx/datasource.py`. `/health` reports `data_mode`. Pipeline and training
  scripts are unaffected by the setting.
- **Tests.** `tests/test_fixture_data.py` and `tests/test_datasource.py`: manifest
  intact, regeneration reproducible, real formats, real QC rules, splits re-derived,
  run-log hashes match the files, the checkpoint reproduces its recorded frozen result,
  the API serves the fixture. `scripts/smoke_api.py` starts uvicorn with the setting and
  checks the answers; added to CI.
- **Memos drafted:** 0011 (tuning grid of 12 per atlas, selection by mean CV balanced
  accuracy, freeze 2 November, CC200 second frozen measurement only as a declared repeat),
  0013 (append-only `runs/analysis_log.jsonl`, the analysis record, all endpoints, error
  contract, CORS), 0014 (fixtures).
- **Clean-up:** memo 0006 note and amendment (871 and 201 are Week 1 figures; QC cohort
  861; Harvard-Oxford 198); `atlas_summary.md` marked superseded; README's "around 80 per
  cent" replaced with Heinsfeld et al. 2018 (70 per cent) and Parisot et al. 2018
  (70.4 per cent), both checked against the papers.
- Tests: 198 passed.
- Pull request: https://github.com/Aleesha-hayat20/NeuroGraph-X/pull/87. CI run on `main` after merge: (paste the link).

### 31 October (Laiba)
- Repository state checked before starting: `main` at `7a2ed45` (PR #89). Suite: 198 passing.
- **CPU inference (memo 0009).** `scripts/predict_one.py` runs one prediction through the
  registry on the CPU and compares it with a reference (`--expect prediction:confidence`,
  tolerance 0.001). CC200 reference: Kaggle GPU result of run `00252f2b`, participant
  `0050011`, control, 0.7052. Works on the fixture data with `NGX_DATA=fixtures`. Documented
  in `SETUP.md`, section 10. `requirements-model.txt` was not created: PyTorch 2.11.0 and
  PyTorch Geometric 2.8.0.post1 are already pinned in `requirements.txt` since PR #38, and
  the main CI job runs the model tests with them.
- **Checkpoint paths (memo 0014 open item).** `inference.checkpoint_path` resolves the
  registry's relative path against the data root holding the registry, through
  `datasource.checkpoint()`, so fixture and real checkpoints load from any working
  directory. Existing callers unchanged.
- **Out-of-fold probabilities.** `train_gnn.py --stage cv` writes
  `runs/oof/<atlas>_<run_id>_oof.csv` (one row per development participant, checked: every
  participant once, no frozen participant, probabilities in 0 to 1) and records its path,
  SHA-256 and count under `metrics.oof`, plus `cv_seconds` and per-fold `seconds` for memo
  0011's timing check. Inside `metrics`, so the database schema does not change.
- **Tests:** `tests/test_oof.py` (unit tests, and the real `cv` stage on the fixture dataset in
  a scratch folder) and a checkpoint-path test in `tests/test_inference.py`. 209 passed.
- **Memos drafted:** 0009 (serving checkpoints), 0010 (calibration).
- **Baseline CV, AAL, Harvard-Oxford, Dosenbach 160** (memo 0006 settings, development
  pool of 761 only, no frozen measurement), notebook
  `notebooks/neurographx-w4-baseline-cv-three-atlases.ipynb`, Kaggle T4, code `273ed4a`.
  Each atlas ran twice in the same session; both runs are kept in the log with their OOF files.

  | Atlas | Run | CV accuracy (SD) | Balanced | AUC | Epochs | Seconds |
  |---|---|---|---|---|---|---|
  | AAL | `d0d6ab7b` | 0.6715 (0.0145) | 0.6681 | 0.6967 | 30 | 98.4 |
  | AAL | `bc8c9ab8` | 0.6741 (0.0184) | 0.6629 | 0.7006 | 22 | 98.6 |
  | Harvard-Oxford | `4908c681` | 0.6518 (0.0188) | 0.6418 | 0.6546 | 38 | 97.6 |
  | Harvard-Oxford | `fe849e36` | 0.6570 (0.0230) | 0.6500 | 0.6594 | 36 | 97.0 |
  | Dosenbach 160 | `f7f49989` | 0.6334 (0.0246) | 0.6277 | 0.6260 | 48 | 121.2 |
  | Dosenbach 160 | `0248d655` | 0.6281 (0.0219) | 0.6220 | 0.6334 | 60 | 120.7 |

  Majority baseline 0.5401 for all. Same seed, different results by up to 0.7 points:
  GPU message passing is not bit-for-bit deterministic (memo 0006), so differences below
  about 1 point between tuning settings are noise. Memo 0011 timing check: about 100 to
  120 s per CV run, so the 48 tuning runs take roughly 2.5 GPU hours; the grid fits and
  does not need shrinking.
- **CPU check on the Mac:** (paste `predict_one.py` output from Aleesha's Mac).
- Pull request: (paste the link).

## Decisions taken
- `docs/decisions/0011-tuning-protocol.md` (proposed)
- `docs/decisions/0013-analysis-log-and-api-contract.md` (proposed)
- `docs/decisions/0014-fixture-data.md` (proposed)
- `docs/decisions/0009-serving-checkpoints.md` (proposed)
- `docs/decisions/0010-calibration.md` (proposed)

## Week close, Sunday 25 October
**Gate items met:** (tick in `plan.md` and list here)
**Gate items missed, and why:**
**Carried into next week:** memos 0011, 0013, 0014 to be accepted at the Thursday stand-up;
open items for Laiba (checkpoint paths through `datasource.checkpoint()`, class-weighted
loss, `repeat_reason`) and Alishba (dashboard against `make api-fixtures`, CORS).
**Board screenshot:** `board.png`
