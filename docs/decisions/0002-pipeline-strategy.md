# 0002. Preprocessing pipeline and strategy

**Status:** Proposed
**Date:** 2026-09-28
**Owner:** Aleesha Hayat

## Context

ABIDE Preprocessed offers four pipelines (CCS, CPAC, DPARSF, NIAK), each with four
strategies covering band-pass filtering on or off and global signal regression on or off.
That is sixteen versions of the dataset. The choice changes results.

## Decision

Fix one pipeline and one strategy for the whole project and declare it in `configs/data.yaml`.

Provisional: **CPAC**, strategy **filt_global**.

## Rationale

The pipeline is not varied because the compute cost of a fifth axis is multiplicative and
outside the FYP-I and FYP-II budget. Fixing it and stating it openly is the honest option.

## To confirm before this moves to Accepted

- [ ] Identify which pipeline and strategy the baseline papers we compare against used.
- [ ] Match that choice so the numbers mean the same thing.
- [ ] Record the check here with the reference.

## Consequences

- Pipeline variability becomes a stated limitation rather than a measured axis.
- A jury question about it has a prepared answer: it is a legitimate fifth axis, the cost
  is multiplicative, and the choice is declared rather than hidden.
