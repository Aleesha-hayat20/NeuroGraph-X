# 0010. Confidence calibration

**Status:** Proposed. For acceptance at the Week 5 Thursday stand-up. Implementation is
Week 6 (W6-04), after the final models of memo 0011.
**Date:** 2026-10-31
**Owner:** Laiba Afridi
**Related:** 0005 (frozen set), 0006 (confidence), 0009 (serving checkpoints), 0011 (tuning
protocol, section 4), 0012 (dashboard display rules), 0013 (analysis record, regenerate)

## Context

Every prediction carries a `confidence`: the softmax probability of the predicted class,
between 0.5 and 1 (memo 0006). It is returned with `calibrated: false`, and the dashboard
labels it "not calibrated" (memo 0012), because nothing yet says that a confidence of 0.70
is right about 70 per cent of the time. Small networks trained on unbalanced data are often
over- or under-confident, and ours leans towards the larger class (frozen set: 25 of 46
autism and 38 of 54 controls correct, run `00252f2b`).

Calibration fixes the meaning of the number without changing which participants the model
ranks higher. It needs predictions the model made on participants it did not train on.
From Week 4, every cross-validation run writes exactly those: the **out-of-fold (OOF)
probabilities**, one per development participant, in `runs/oof/<atlas>_<cv run_id>_oof.csv`,
with the file's SHA-256 in the run log (`metrics.oof`). The frozen set is never used to fit
anything (memos 0005 and 0011).

## Decision

### 1. What is calibrated

The model's probability of autism, `p = softmax(logits)[autism]`. The calibrated
probability `q` replaces `p`, and the confidence becomes `max(q, 1 - q)`; the prediction is
autism when `q >= 0.5`. One calibrator per atlas, for that atlas's final model.

### 2. Method: Platt scaling, declared now

`q = sigmoid(a * logit(p) + b)`, two numbers per atlas, fitted by logistic regression on the
OOF table of the cross-validation run that memo 0011 selected for that atlas.

- Temperature scaling (`b = 0`) cannot correct a shift towards one class; `b` can.
- Isotonic regression is rejected: with about 761 points per atlas it fits a step function
  that overfits, and it can change the order of participants.
- The method is fixed here, before any OOF result is seen, so it is not chosen by its score.

### 3. Data, and what is never used

- Fitted on the selected CV run's OOF table only (761 development participants per atlas).
  `check_oof` (Week 4) refuses an OOF table that misses a development participant, repeats
  one, or contains a frozen participant.
- The OOF table belongs to the CV run whose settings the final model used, so the
  calibrator matches the model it is applied to. CC200's baseline CV run `df8dd345` predates
  OOF files; if the baseline configuration wins the tuning, the grid's baseline run (same
  settings and seed) supplies the OOF table.
- Never fitted on, tuned on, or chosen by the frozen set.

### 4. How it is judged

| Measure | Definition | Where |
|---|---|---|
| Expected calibration error (ECE) | Probabilities of autism in 10 equal-width bins over 0 to 1; the size-weighted mean of the gap between the bin's mean probability and its share of autism participants | OOF, and frozen |
| Brier score | Mean squared difference between probability and label (0 or 1) | OOF, and frozen |
| Reliability diagram | Bin mean probability against observed share, with bin counts | report figure |

- **On OOF, cross-fitted:** fit on four folds' OOF rows, apply to the fifth, rotate. This
  reports calibration on rows the calibrator did not see. The calibrator that is served is
  then fitted once on all OOF rows.
- **On the frozen set, before and after:** computed from the same single set of frozen
  predictions as the frozen accuracy, so it is not an extra measurement (memo 0011,
  section 4). That set must be kept: from Week 5, `train_gnn.py --stage final` writes the
  frozen per-participant probabilities to `runs/frozen_predictions/<atlas>_<run_id>.csv`
  (Laiba). For `00252f2b`, which predates this, they are regenerated from its checkpoint,
  which reproduces its predictions exactly (`reload_identical: true`); nothing is chosen
  from them.
- Accuracy and AUC are reported unchanged by calibration (Platt scaling keeps the order);
  if a calibrated prediction flips at 0.5, the flip count is reported.

### 5. Storage and use

- One file per calibrated model: `runs/calibration/<atlas>_<final run_id>.json` with
  `method`, `a`, `b`, `cv_run_id`, `oof_sha256`, `n`, the OOF and frozen ECE and Brier
  before and after, and `fitted_at`. A separate file, not a new registry field, so the
  database schema and memo 0008 do not change.
- `inference.predict` applies the file for the served `run_id` when it exists and then
  returns `calibrated: true`; without it the answer stays `calibrated: false`. Regenerate
  (memo 0013) applies the original run's file exactly as before.
- `GET /models/{atlas}` (memo 0013) reports the calibration file's numbers with the
  registry entry. The dashboard drops "not calibrated" only when `calibrated` is true
  (memo 0012).

## Rationale

- **Two parameters** cannot overfit 761 points and cannot reorder participants, so the
  frozen accuracy and AUC stay exactly as measured.
- **OOF data** is the only honest fitting data available without touching the frozen set.
- **Declaring the method and the measures now**, before the tuned models exist, keeps
  calibration from becoming another choice made by looking at results.
- **A file per run** ties a calibrator to one checkpoint, which regenerate needs.

## Consequences

- Week 4 (this memo's pull request): OOF files from every CV run, with checks and tests.
- Week 5 (Laiba): frozen per-participant probabilities saved by the final stage.
- Week 6 (Laiba, W6-04): `calibration.py` (fit, cross-fitted ECE and Brier, write the file),
  `inference.predict` applies it, tests on fixture data, reliability diagrams for the report.
- The report states calibration results per atlas from OOF and from the frozen set, and
  never presents a calibrated confidence as a diagnostic probability.

## To confirm

- [ ] Accepted at the Week 5 Thursday stand-up, before any OOF table is looked at.
- [ ] Alishba: the dashboard reads `calibrated` and the model endpoint's calibration fields.
- [ ] Aleesha: the integrity check (Week 6) verifies each calibration file's `oof_sha256`
  against its CV run.
