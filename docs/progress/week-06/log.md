# Week 6 log

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

## Decisions taken
- `docs/decisions/0009-serving-checkpoints.md`: option A (final checkpoints in the repository).
