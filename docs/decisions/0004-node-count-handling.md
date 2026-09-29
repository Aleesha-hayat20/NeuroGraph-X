# 0004. Handling different node counts across atlases

**Status:** Accepted
**Date:** 2026-09-28
**Owner:** Laiba Afridi

## Context

The four selected atlases define different numbers of regions, so the graphs they produce
have different numbers of nodes. A single model cannot consume all four without either a
size-agnostic readout or one model per atlas.

## Decision

**One trained model per atlas**, with the atlas recorded in the model registry alongside
the checkpoint.

## Rationale

Simpler than a size-agnostic readout, consistent with what was presented at the idea
defence, and the cost is a factor of four in training runs which is already budgeted.

## Consequences

- Four checkpoints in the registry rather than one.
- Every cell of the reliability grid is multiplied by four.
- The inference API must select the checkpoint that matches the requested atlas.
