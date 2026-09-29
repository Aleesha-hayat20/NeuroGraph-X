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

## To confirm

- [ ] Confirm the exact motion column name from the Week 1 metadata report.
- [ ] Set the final threshold from the observed distribution, and record it here with the
      date, before any model is trained.
- [ ] Record the retained and excluded counts once the screen has run.

## Consequences

- The retained cohort size is an output of this decision, not an input.
- The exclusion log is a deliverable and is shown at the midterm.
