# Week 6 log

## Monday 2 November, stand-up
**Tuning freeze (memo 0011):** from this day no tuning setting changes. All 48 runs of the
grid are dated before the freeze (checked in the review of #94).
**Next:** tasks in `plan.md`.

## Entries

### 5 to 8 November (Laiba): tuning committed, final models, calibration
- **Tuning (memo 0011) committed and selected (#94):** 48 CV runs, all logged before the
  2 November freeze; density 0.05 selected on all four atlases (class weights on for AAL
  only), hidden 64. Gains over the baseline +0.009 to +0.026, within the fold SD.
- **Schema 3 (#94):** `--allow-repeat` requires `--repeat-reason`; the run log records
  `repeat_reason` and `checkpoint_sha256`; the loader refuses a checkpoint that does not
  match its logged hash.
- **`GET /models`, `GET /models/{atlas}` (#118, closes #74, #75).**
- **Calibration (memo 0010, #77, PR #126):** Platt scaling fitted on each selected CV run's
  OOF table; refuses a slope <= 0 (it would reverse the ranking); hash checks accept
  either line ending (found in #93's review).
- **Final models, frozen set measured once each (#96, #97, PR #126), Kaggle commit run on
  code `942f65f`, 8 November:**

  | Atlas | Final run | Frozen acc. (95% CI) | Balanced | AUC | ECE frozen before → after |
  |---|---|---|---|---|---|
  | AAL | `57900b0d` | 0.65 (0.55–0.74) | 0.652 | 0.666 | 0.250 → 0.096 |
  | CC200 (declared repeat) | `cf60f29e` | 0.55 (0.45–0.64) | 0.548 | 0.625 | 0.398 → 0.168 |
  | Harvard-Oxford | `76533df4` | 0.63 (0.53–0.72) | 0.624 | 0.682 | 0.334 → 0.185 |
  | Dosenbach 160 | `5ee28510` | 0.62 (0.52–0.71) | 0.618 | 0.668 | 0.359 → 0.052 |

  Majority baseline 0.54 for all.
- **CC200 below its baseline.** The tuned model (`cf60f29e`, 0.55) scored below the
  baseline `00252f2b` (0.63). The intervals overlap and the CV gain was below fold noise.
  The pre-registered selection is kept (memo 0011): choosing by frozen score would turn
  the frozen set into a tuning set. `00252f2b` stays in the run log and in the registry's
  `previous_run_ids`.
- **First commit run stopped before any measurement.** The first Kaggle commit (8
  November) copied an older code version from the input and failed at the tests
  (section 4), before the frozen set was read. The notebook now picks the Week 6 code
  folder explicitly and stops within seconds otherwise (`942f65f`); the second run is the
  one in the log.
- **Imported with every hash checked** (`scripts/import_results.py`); model cards and
  `docs/reports/final_results.md` generated from the logs (`scripts/make_model_cards.py`,
  #99).
- **`POST /analyses` (#73, PR #126)** once the analysis-log writer was merged (#119).
- **Checkpoints committed (memo 0009 option A, accepted 12 November, #98)** with the
  licence note in `checkpoints/README.md`.

### 8 to 17 November (Aleesha): regenerate, export, integrity and confound checks; report structure
- Branch `feature/week6-regenerate-integrity`, started from `main` at `421de9c` (Laiba's
  #126 and Alishba's #124, #125 and #127 to #129 merged); 341 tests passed there.
- **Memo decisions.** 0009 accepted on 12 November with option A and five checkpoints: the
  four registered models and the CC200 baseline `00252f2b`, whose frozen-set result the
  report compares with the declared repeat. 0010, 0011, 0013 and 0014 recorded as accepted
  at the Week 5 Thursday stand-up; their open items closed.
- **Review of #158.** Four changes requested on 12 November (five checkpoint files, one
  `.gitignore` line per file, the README's acceptance date and the ABIDE and Preprocessed
  Connectomes Project citations, no empty sections in this log). On 13 November the five
  checkpoints matched the SHA-256 values in the run log and #158 was merged.
- **W6-06 regenerate, W6-07 export** (`src/neurographx/api/reproduce.py`).
  `POST /analyses/{analysis_id}/regenerate` re-runs the participant and atlas with the
  model of the original analysis's training run, even after the registry has moved to a
  newer model, records the repeat with `reproduces_analysis_id`, and returns
  `{analysis, original, identical, differences}`. `GET /analyses/{analysis_id}/export`
  returns `analysis_<id>.json` or `analysis_<id>.csv`. Both follow the error contract (404
  unknown analysis; 422 unknown format; 503 when the original run or its checkpoint is not
  available). POST /analyses and regenerate share one graph builder and one inference path.
- **Integrity check** (`scripts/check_integrity.py`, `src/neurographx/integrity.py`): seven
  sections, from the run log to the analysis log; step added to CI on the fixture dataset.
  Finding while building it: the connectome file hashes in the run log are those of the
  Kaggle builds, and the Mac's store has other file hashes. The arrays are the same (the
  Mac's HO store and a rebuild with numpy 2.0.2 are bit-identical, yet the two files hash
  differently), so the check replays each registered model on its saved frozen-set
  predictions instead: the same probabilities mean the same inputs. Text files are compared
  with LF or CRLF line endings, and `.gitattributes` now keeps them LF on every platform.
- **Integrity check on the real data** (13 November, after #158): `38 passed, 0 failed,
  3 warnings`. All four registered models reproduce their saved frozen-set probabilities on
  the Mac's CPU for all 100 participants, with a largest difference of 0.000001 (AAL, CC200,
  Harvard-Oxford) and 0.000002 (Dosenbach 160) against a tolerance of 0.001, so the Mac's
  connectome store gives the models the inputs they were trained and measured on. The three
  warnings concern the Week 3 baseline `00252f2b`, logged before checkpoint hashes,
  out-of-fold files and frozen-prediction files existed.
- **Confound check** (`scripts/confound_check.py`): out-of-fold accuracy by site, by motion
  quartile and with flat regions, in `docs/reports/confound_check.md`, written as a
  limitation analysis. The pooled out-of-fold accuracy equals the logged cross-validation
  accuracy of each selected configuration (0.6833, 0.6873, 0.6754, 0.6583).
- **Real-data rehearsal** on the Mac (13 and 17 November), API in real mode, frozen-set
  participant `0050011`: CC200 (`cf60f29e`) `control` 0.5124 and Harvard-Oxford
  (`76533df4`) `autism` 0.6174, both calibrated. Regenerate of the CC200 analysis, run
  twice, reported identical with no differing field both times; the JSON and CSV exports
  held the stored record; an unknown analysis and an unknown export format returned their
  documented 404 and 422 messages. The same analysis run from the dashboard showed
  `control`, 51.2%, calibrated, run `cf60f29e`; History listed every analysis and Models
  showed the four atlases with their reliability diagrams. The rehearsal records were then
  removed from `runs/analysis_log.jsonl`, which holds only demonstration analyses (memo
  0013).
- **Report and SRS.** `docs/report/README.md` holds the Report v2.0 structure in the
  handbook layout, the chapter owners, the formatting rules, the schedule and the sources
  for each chapter. The report is written in a shared document private to the team, and
  its PDF is added to the repository once submitted. `docs/report/srs.md` is SRS version
  1.1, with a verification table from each requirement to its tests.
- Weeks 1, 2, 4 and 5 logs completed from the records; a Week 5 test that assumed an empty
  fixture analysis log now counts the records present.
- Tests: `390 passed`; ruff clean; smoke test and integrity check pass on the fixtures.

## Decisions taken
- `docs/decisions/0009-serving-checkpoints.md`: option A, accepted 12 November; the four
  final checkpoints and the CC200 baseline are in the repository.
- `docs/decisions/0010-calibration.md`, `0011-tuning-protocol.md`,
  `0013-analysis-log-and-api-contract.md` and `0014-fixture-data.md`: recorded as accepted
  at the Week 5 Thursday stand-up (29 October).
- Report v2.0 is written in a shared document private to the team; the repository keeps
  its structure (`docs/report/README.md`) and, after submission, the final PDF.

## Week close
**Planned for Sunday 8 November; closed on Tuesday 17 November.** The final checkpoints
waited for the memo 0009 decision (12 November), and the real-data checks and the
rehearsal needed them.
**Gate items met:** all six. Four calibrated models registered (PR #126), their
checkpoints committed and matching the hashes their runs recorded (PR #158); each atlas
measured once on the frozen set after the tuning freeze, CC200 as the declared repeat
(`cf60f29e`, reason logged); an analysis run end to end on real data through the dashboard;
the integrity check passing in CI and on the real data; the end-to-end test passing in CI
(PR #129); the report structure and SRS v1.1 committed.
**Carried into next week:** the dashboard's regenerate and export controls and its
Overview and Exclusions pages, and the as-built diagrams (Alishba); performance tests and
the API reference (Laiba); the reliability engine skeleton and manual test round 1
(Aleesha); report chapters (all).
