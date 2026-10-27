# 0011. Tuning protocol and frozen-set re-measurement policy

**Status:** Proposed. Must be accepted **before the first tuning run**: at the Week 5
Monday stand-up (26 October 2026) if tuning starts that week, and no later than the
Thursday stand-up (29 October).
**Date:** 2026-10-24
**Owner:** Aleesha Hayat (protocol); Laiba Afridi runs the tuning
**Related:** 0004 (one model per atlas), 0005 (frozen evaluation set), 0006 (model
architecture, amendment of 12 October), 0008 (database schema), 0010 (calibration)

## Context

Week 5 tunes the model on cross-validation for all four atlases, and Week 6 trains the
four final models. Two things can quietly make the reported numbers too optimistic:

1. **Choosing among many settings.** The best of twelve cross-validation scores is higher
   than the true performance of that setting, simply because it was picked for being high.
2. **Looking at the frozen set more than once.** The frozen evaluation set (memo 0005) is
   only an honest test if no decision ever depends on it. Each extra measurement that can
   influence a choice turns it into a second validation set.

CC200 has already been measured once on the frozen set, before any tuning:

| Run | Stage | Result |
|---|---|---|
| `df8dd345` | cross-validation, 761 development participants, 5 folds | accuracy 0.6728 (SD 0.0147), balanced accuracy 0.6672 (SD 0.0119), AUC 0.6987 |
| `00252f2b` | final model, frozen set of 100 | accuracy 0.63, balanced accuracy 0.6236, AUC 0.655; majority-class baseline 0.54 |

Source: `runs/run_log.jsonl` and `runs/model_registry.json`. The other three atlases have
not been measured on the frozen set.

This memo fixes, **before tuning starts**, what may be tuned, how the winner is chosen,
when tuning stops, and how often each atlas may touch the frozen set.

## Decision

### 1. The grid is declared now and not extended

| Setting | Values | Baseline (memo 0006) |
|---|---|---|
| Edge density (proportion of strongest connections kept) | 0.05, 0.10, 0.20 | 0.10 |
| Class-weighted loss | off, on | off |
| Hidden units | 32, 64 | 64 |

That is **12 configurations per atlas, 48 in all**, each a 5-fold cross-validation run.
Everything else stays at the memo 0006 values: 3 GCN layers, dropout 0.5, Adam with
learning rate 0.001, batch size 32, at most 100 epochs, the best epoch chosen per fold on
that fold's validation part, the final epoch count the median across folds, flat regions
filled with 0, seed 42.

- **Class-weighted loss**, in plain words: mistakes on the smaller group cost more, so the
  model cannot do well by mostly predicting the larger group. Weight for class *c* =
  (training participants) / (2 x training participants in class *c*), computed on each
  training fold only, never on the validation fold or the frozen set. This is not yet in
  `scripts/train_gnn.py` (Laiba, Week 5); it is recorded as `"class_weighted": true/false`
  in the run's `hyperparameters`.
- **One seed for every configuration.** Seeds are not searched. How much results move with
  the seed is the question of the reliability module in FYP-II, not a tuning knob.
- **Every configuration is run, once.** No configuration is dropped or repeated after its
  result is seen.
- Each tuning run carries `"tuning_grid": "0011-v1"` in its `data_config`. Both
  `hyperparameters` and `data_config` are JSON columns (memo 0008), so neither field needs a
  schema change.
- **If the grid will not fit the free GPU budget,** Laiba uses the wall-clock time of the
  Week 4 baseline runs to say so before tuning starts, and the grid shrinks by an amendment
  here, in this order: drop hidden 32, then drop density 0.05. It never shrinks after
  results are in.

### 2. How the winner is chosen

1. **Criterion: highest mean cross-validation balanced accuracy** across the 5 folds.
   Balanced accuracy is the average of the accuracy on autism participants and the
   accuracy on control participants, so a model that favours the larger group cannot win.
   The cohort is not balanced (396 autism, 465 control), which is why plain accuracy is not
   used.
2. **Ties:** two configurations within 0.005 of each other count as tied. A tie goes to the
   configuration with fewer changes from the baseline; if still tied, to the lower
   standard deviation across folds.
3. **Selection is done by script, from the run log**, not by eye, and the full table of all
   12 configurations per atlas with the chosen one marked is written to
   `docs/reports/tuning_selection.md`. Proposed: `scripts/select_config.py` (Laiba, with
   Aleesha reviewing).
4. **The selected configuration's cross-validation score is reported as optimistic.** It
   won a contest of twelve, so it is reported next to the frozen-set result, never instead
   of it.

### 3. The tuning freeze: Monday 2 November 2026

Tuning runs may be logged up to Sunday 1 November. Selection is made on Monday 2 November
from the runs logged by then. After the freeze no setting changes for FYP-I; a tuning run
logged later is ignored for selection and the selection table says so.

### 4. The frozen set after the freeze

| Atlas | Frozen-set measurements |
|---|---|
| AAL, Harvard-Oxford, Dosenbach 160 | **Exactly one**, after the freeze, with `scripts/train_gnn.py --stage final --epochs-from-cv <selected run>` |
| CC200 | The first (`00252f2b`) stays in the log and the report. If the selected configuration differs from the baseline, the selected model is measured once more as a **declared repeat** (`--allow-repeat`, reason "post-tuning measurement per memo 0011"). If the baseline configuration wins, there is no second measurement and `00252f2b` remains the final CC200 model |

Rules that hold for every atlas:

- The frozen-set result **never** feeds back into a choice: no re-tuning, no swapping
  configurations, no picking the better of two frozen numbers.
- Both CC200 numbers are reported side by side when there are two. The registry serves the
  later model and keeps `00252f2b` under `previous_run_ids`.
- Any other frozen measurement (for example after a bug fix) needs an amendment to this memo
  **before** the run, naming the reason. The report states how many times each atlas was
  measured.
- Calibration (memo 0010) is fitted on the selected cross-validation run's out-of-fold
  predictions. Its effect on the frozen set (expected calibration error before and after)
  is computed from the same single set of frozen predictions, so it is not an extra
  measurement.

### 5. Recording the reason for a repeat

Today a repeat is recorded only as `repeat_frozen_measurement: true`. The reason should be in
the log too. Proposed for Week 5:

- a new optional run-log field `repeat_reason` (text), required by `scripts/train_gnn.py`
  whenever `--allow-repeat` is given (Laiba);
- the matching nullable column in `db/schema.sql`, `RUN_LOG_COLUMNS` and the ER diagram,
  with `schema_version` raised to 3 as memo 0008 requires (Alishba);
- the integrity check (Week 6, Aleesha) fails if an atlas has more than one final run and
  any run after the first lacks `repeat_frozen_measurement: true` and a `repeat_reason`.

## Rationale

- **A small grid declared in advance** keeps tuning inside free GPU time and makes the
  selection bias small and visible. The three settings are the ones the FYP-I work plan
  names (Section 8.4): edge density, which memo 0006 already treats as a hyperparameter;
  class balance; and model size.
- **Balanced accuracy** is honest on an unbalanced cohort, and it is also how the frozen
  result is judged against the majority-class baseline (0.54).
- **A fixed freeze date** turns "we stopped when it looked good" into "we stopped on the
  date we wrote down".
- **Declaring CC200's repeat rather than hiding it** is the only honest option once a
  number has been seen. The first measurement was made before tuning and did not steer the
  grid, which comes from the work plan, but it was seen, so it is reported.
- **How much to read into differences.** With 100 frozen participants, the 95 per cent
  margin of error on an accuracy near 0.63 is roughly plus or minus 9.5 percentage points
  (1.96 x the square root of 0.63 x 0.37 / 100). Differences of a few points between
  atlases, or between CC200's two measurements, are within that margin and are not
  presented as one atlas "beating" another.

## Consequences

- Laiba adds class-weighted loss and the `tuning_grid` tag to `scripts/train_gnn.py` before
  the first tuning run (Week 5).
- `docs/reports/tuning_selection.md` becomes a report artefact and a source for the
  results chapter.
- The final metrics table has one row per atlas plus, at most, a second CC200 row marked as
  a declared repeat.
- Week 5 tuning cannot start until this memo is accepted.

## To confirm

- [ ] Laiba: baseline cross-validation timings for AAL, Harvard-Oxford and Dosenbach 160
  confirm that 48 runs fit before 1 November, or the grid is shrunk here first.
- [ ] Laiba: class-weighted loss and the `tuning_grid` tag implemented, with a unit test.
- [ ] Alishba and Laiba: `repeat_reason` added to the logger, schema and ER diagram.
- [ ] Accepted at a stand-up, before tuning starts.
