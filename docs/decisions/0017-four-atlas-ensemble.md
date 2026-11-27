# 0017. The four-atlas ensemble, reported beside the single-atlas models

**Status:** Accepted on 24 November 2026 (option 1 of Section 0). Proposed by Laiba Afridi
on 23 November 2026, after the supervisor suggested combining the four atlas models. The
ensemble is evaluated on the frozen set only after this memo is merged.
**Date:** 2026-11-23, revised 2026-11-24
**Owner:** Laiba Afridi
**Related:** 0005 (frozen set), 0006 (architecture), 0010 (calibration), 0011 (tuning
protocol and final models), 0013 (analysis record and API contract), 0015 (real-world
repositioning, Section 4.3), 0016 (reliability engine skeleton)

## Context

Memo 0011 trained one final model per atlas and measured each once on the frozen set of
100 participants: accuracy 0.65 (AAL), 0.55 (CC200), 0.63 (Harvard-Oxford) and 0.62
(Dosenbach 160) against a majority baseline of 0.54 (`docs/reports/final_results.md`).
The four atlases divide the same brain differently, so their models make partly different
mistakes, and combining them can cancel some of those mistakes.

This memo fixes one combination rule, and how its result is reported, **before it is
evaluated on the frozen set**. The single models' frozen results were known when the idea
came up, so the decision is not fully blind to the frozen set. That is why the rule has no
setting to tune, its evidence comes from cross-validation only, it is evaluated once, and
its result does not replace the single models' results.

## Decision

### 0. How the ensemble is reported

| Option | Meaning | Decision |
|---|---|---|
| 1. An extra result | One more row beside the four single-atlas models; they stay the main results and the served models | **Accepted** |
| 2. The main result | The ensemble becomes the headline model; the single models become its components | Rejected. It would hide how much the result depends on the atlas, which is the atlas axis of the planned reliability envelope (memo 0015, Section 4.3; memo 0016), and the headline would be a model the platform does not serve |
| 3. Not in FYP-I | Close the work and move it to FYP-II | Rejected. The evidence is ready, nothing is retrained, and the supervisor asked for it |

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

Ensembles of graph convolutional networks have been used on ABIDE before (Anirudh and
Thiagarajan, ICASSP 2019, DOI 10.1109/ICASSP.2019.8683547). Theirs combine weakly trained
networks built on different population graphs, not one model per atlas, so the parallel is
the use of an ensemble, not the exact rule.

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
- It writes one record to `runs/ensemble_log.jsonl` (the four member run IDs, the rule,
  the metrics and the SHA-256 of its prediction file) and refuses to run again if that file
  already holds a measurement, as `train_gnn.py` does for a frozen measurement. The record
  is kept out of the run log, whose database table (memo 0008) holds training runs; an
  ensemble trains nothing. `scripts/check_integrity.py` (section 8) checks the record:
  one measurement per dataset, members that are final runs, and a prediction file that
  matches its hash and is the mean of the members' saved predictions.
- The result is reported **whatever it is**, as one more row beside the four single
  models. It does not replace them as the main results, whether it scores higher or lower
  than any of them: choosing a headline by frozen score would turn the frozen set into a
  tuning set.

### 5. What changes in the platform, and what does not

The four single models, their cards and their calibration stay as they are, and every
analysis is still made by one atlas's model. The API reports the ensemble's recorded
result (members, rule, cross-validation and frozen-set metrics, from
`runs/ensemble_log.jsonl`) through its own endpoint, `GET /models/ensemble`, so that
`GET /models` keeps one entry per atlas model (memo 0013). The Models page shows it as one
extra row, "Ensemble of the four atlases (memo 0017)". A combined prediction for a single
participant, and calibrating the ensemble's confidence, are left for FYP-II.

## Consequences

- The report and the deck present the four single-atlas models as the main results and
  the ensemble as one more row, so the spread between atlases stays visible.
- The comparison with published work (Dong et al. 2025) uses cross-validation numbers on
  both sides; the frozen result is reported separately.
- **Limitation, stated in the report:** the decision to combine was taken after the single
  models' frozen results were known. It is limited, not removed, by fixing the rule here
  from cross-validation alone and evaluating once.
