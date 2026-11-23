# 0017. The four-atlas ensemble as the final model

**Status:** Proposed by Laiba Afridi on 23 November 2026, after the supervisor suggested
combining the four atlas models and the team agreed. Accepted when this memo is merged;
the ensemble is evaluated only after that.
**Date:** 2026-11-23
**Owner:** Laiba Afridi
**Related:** 0005 (frozen set), 0006 (architecture), 0010 (calibration), 0011 (tuning
protocol and final models), 0013 (analysis record)

## Context

Memo 0011 trained one final model per atlas and measured each once on the frozen set of
100 participants: accuracy 0.65 (AAL), 0.55 (CC200), 0.63 (Harvard-Oxford) and 0.62
(Dosenbach 160) against a majority baseline of 0.54 (`docs/reports/final_results.md`).
The four atlases divide the same brain differently, so their models make partly different
mistakes, and combining them can cancel some of those mistakes.

This memo fixes one combination rule and declares it the project's final model **before
it is evaluated on the frozen set**. Those results were known when the idea came up, so
the decision is not fully blind to the frozen set. That is why the rule has no setting
to tune, its evidence comes from cross-validation only, and it is evaluated once.

## Decision

### 1. The rule

For each participant, the ensemble takes the probability of autism `p_a` from each of the
four final models (`a` = AAL, CC200, Harvard-Oxford, Dosenbach 160), the same
`prob_autism` the models already write, and averages them with equal weight:

    p_ens = (p_aal + p_cc200 + p_ho + p_dosenbach160) / 4

It predicts autism when `p_ens >= 0.5`; its confidence is `max(p_ens, 1 - p_ens)`.

- **Raw probabilities**, not the calibrated ones of memo 0010. The cross-validation evidence
  below uses raw out-of-fold probabilities, and calibrating before averaging would mix in
  four fitted calibrators.
- **Equal weights and a fixed threshold of 0.5.** No weight or threshold is learned from
  data, so nothing can be fitted to the frozen set.
- **Models used:** the registered final runs `57900b0d`, `cf60f29e`, `76533df4` and
  `5ee28510` (`runs/model_registry.json`), unchanged. No model is retrained.

Mean (soft-vote) fusion of graph convolutional networks on ABIDE follows Anirudh and
Thiagarajan (2017, arXiv:1704.07487).

### 2. Evidence: cross-validation only

Out-of-fold predictions of the four selected configurations (memo 0011) on the 761
development participants: `runs/oof/aal_d3611e1d_oof.csv`, `cc200_c2516a5f`,
`ho_d1873b17`, `dosenbach160_f9f7e584`. Mean (standard deviation) over the five folds:

| Model | Accuracy | Balanced accuracy | AUC |
|---|---|---|---|
| AAL alone | 0.687 (0.015) | 0.682 (0.012) | 0.697 (0.027) |
| CC200 alone | 0.683 (0.026) | 0.678 (0.023) | 0.696 (0.010) |
| Harvard-Oxford alone | 0.675 (0.019) | 0.670 (0.027) | 0.680 (0.024) |
| Dosenbach 160 alone | 0.658 (0.026) | 0.651 (0.022) | 0.644 (0.038) |
| **Mean probability (this rule)** | **0.695 (0.020)** | **0.687 (0.018)** | **0.750 (0.037)** |
| Mean logit | 0.669 (0.027) | 0.662 (0.020) | 0.721 (0.045) |
| Majority vote, 2–2 tie to control | 0.703 (0.019) | 0.689 (0.019) | 0.775 (0.034)* |

\* AUC of the vote share (0, 1/4, ... 1).

### 3. Why not the majority vote

The majority vote scored a little higher. It is still not chosen, because with four models
123 of the 761 participants (16%) get a 2–2 tie, and the vote's result depends on how a tie
is broken: accuracy 0.703 with ties to control, 0.725 with ties to autism, 0.702 with ties
settled by the mean probability. The tie rule would be one more setting chosen by its score
on the same folds, the kind of selection memo 0011 warns inflates cross-validation. The mean
probability has no such choice. The mean logit is rejected because a single over-confident
model (probability near 0 or 1) dominates the average of logits.

### 4. How it is evaluated, once

- `scripts/ensemble.py` (separate pull request, merged after this memo) reads the four
  final runs' saved frozen-set predictions (`runs/frozen_predictions/*_frozen.csv`). It
  first checks each file's SHA-256 against the run log, and checks that all four list the
  same 100 participants with the same labels. Then it computes the ensemble.
- It reports accuracy with a 95% Wilson interval, balanced accuracy, AUC, the confusion
  matrix and the majority baseline, as for the single models.
- It writes one run-log record (`stage: "ensemble"`, the four member run IDs, the metrics
  and the SHA-256 of its prediction file) and refuses to run again if such a record
  exists, as `train_gnn.py` does for a frozen measurement.
- The result is reported **whatever it is**, beside the four single models. The ensemble
  stays the final model even if a single atlas scored higher on the frozen set; choosing
  between them by frozen score would turn the frozen set into a tuning set.

### 5. What does not change

The four single models, their cards and their calibration stay as they are, and the API
and dashboard keep serving them. Serving the ensemble through the API is a separate
decision for the team. The ensemble's confidence is uncalibrated; calibrating it is left
for FYP-II.

## Consequences

- The report gives one headline result, the ensemble, and keeps the four single models
  as its components.
- The comparison with published work (Dong et al. 2025) uses cross-validation numbers on
  both sides; the frozen result is reported separately.
- **Limitation, stated in the report:** the decision to combine was taken after the single
  models' frozen results were known. It is limited, not removed, by fixing the rule here
  from cross-validation alone and evaluating once.
