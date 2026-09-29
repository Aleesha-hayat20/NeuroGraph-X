# 0005. Frozen evaluation set

**Status:** Proposed
**Date:** 2026-09-28
**Owner:** Aleesha Hayat

## Context

Every run in both semesters must be measured against the same held-out participants, or
results from different runs cannot be compared. If any evaluation participant is ever seen
during training, every number becomes meaningless. That failure is called data leakage.

## Decision

- **Size:** 100 participants.
- **Stratification:** by `SITE_ID` and `DX_GROUP` together, so the set is not dominated by
  a few hospitals or skewed toward one group.
- **Drawn once**, with the seed recorded in `configs/data.yaml`.
- **Committed** to the repository at `data/frozen/frozen_eval_100.csv` as a list of subject
  identifiers. It is the one thing under `data/` that is version controlled.
- **Never regenerated.**

## Enforcement

A pytest test asserts that no identifier in the frozen file appears in any training split.
It runs in CI on every push, so leakage fails the build rather than reaching a result.

## To confirm

- [ ] Draw the set once the quality control screen has run, so it is drawn from retained
      participants only.
- [ ] Record the retained cohort size and the per-site composition here.
- [ ] Commit the file and confirm the leakage test passes in CI.
