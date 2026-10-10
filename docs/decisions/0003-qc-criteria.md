# 0003. Quality control criteria

**Status:** Accepted
**Date:** 2026-09-28
**Owner:** Aleesha Hayat

> These criteria were recorded on the date above, **before any classification result was
> produced**. That is what makes them defensible. Changing them after seeing a result
> invalidates everything downstream.

## Context

Participants must be screened before entering the pipeline, and the screening must not be
tunable against results.

## Decision

Three gates, applied in order, with every exclusion written to the exclusion log with its
reason.

**1. Rater criteria.** Following the convention used by
`nilearn.datasets.fetch_abide_pcp(quality_checked=True)`, version 0.14.1:

| Column | Accepted values |
|---|---|
| `qc_rater_1` | OK |
| `qc_anat_rater_2` | OK, maybe |
| `qc_func_rater_2` | OK, maybe |
| `qc_anat_rater_3` | OK |
| `qc_func_rater_3` | OK |

**2. Head motion.** A threshold on the mean framewise displacement column, applied only if
that column exists in the phenotypic file. Provisional threshold 0.5 mm.

**3. Completeness.** The derivative file must exist and the time series must be non-empty.

## Confirmation (closed 2026-10-06)

Closed before any model was trained on ABIDE data. Laiba's Week 1 training run used a
standard toy graph dataset, not ABIDE, so no ABIDE result existed when this was fixed.

- [x] Confirm the exact motion column name from the Week 1 metadata report.
  `func_mean_fd` (mean framewise displacement, mm), present for 1099 of 1112 rows
  (`docs/reports/metadata_report.md`, section 7).
- [x] Set the final threshold from the observed distribution, and record it here with the
      date, before any model is trained.
  **0.5 mm**, kept from the provisional value, decided 2026-10-06. Among the 871
  participants who pass the rater gate, mean FD has median 0.078 mm and maximum 1.435 mm;
  10 exceed 0.5 mm, 41 exceed 0.3 mm and 91 exceed 0.2 mm. 0.5 mm removes the clear
  outliers while keeping small sites usable for site stratification. A missing motion
  value fails the gate (none occur among rater-passing participants).
  Declared in `configs/qc_criteria.yaml`.
- [x] Record the retained and excluded counts once the screen has run.
  Run with `scripts/05_apply_qc.py`:

  | Step | Participants |
  |---|---|
  | In the phenotypic file | 1112 |
  | Excluded at the rater gate | 241 |
  | Excluded at the motion gate | 10 |
  | Excluded at the completeness gate | 0 |
  | **Retained (QC cohort)** | **861** (396 autism, 465 control, 20 sites) |

  Cohort: `data/splits/qc_cohort.csv`. Exclusion log with every reason:
  `docs/reports/exclusion_log.csv`. The completeness gate is checked only for
  rater-passing participants, because only they were downloaded in Week 1.

## Consequences

- The retained cohort size is an output of this decision, not an input.
- The exclusion log is a deliverable and is shown at the midterm.
