# 0001. Atlas selection

**Status:** Accepted
**Date:** 2026-09-28
**Owner:** Aleesha Hayat

## Context

ABIDE Preprocessed provides region time series for seven atlases: AAL, CC200, CC400,
Dosenbach 160, EZ, Harvard-Oxford and Talairach. The project uses four. The choice of
atlas is one of the four axes of the reliability envelope, so the four must differ in a
way that makes the axis meaningful.

## Decision

Four atlases, chosen so that each defines a brain region on a different basis.

| Atlas | Derivative key | How regions are defined | Why it earns its place |
|---|---|---|---|
| AAL | `rois_aal` | Anatomical, from macroanatomical landmarks | The standard anatomical reference |
| CC200 | `rois_cc200` | Functional, data-driven clustering | The most widely used atlas in the ABIDE classification literature, so results are comparable with published work |
| Harvard-Oxford | `rois_ho` | Probabilistic, built from a population | A different statistical basis again |
| Dosenbach 160 | `rois_dosenbach160` | Meta-analytic network nodes, spheres rather than full coverage | Structurally unlike the other three, network-based by construction |

Pilot atlas for the Week 1 end to end check: **CC200**.

## Rationale

Choosing four similar atlases would make the atlas axis test almost nothing. AAL, EZ and
Talairach are all anatomical, and CC400 is the same family as CC200. Taking one atlas from
each family means that when the reliability engine varies the atlas, it is varying the
underlying idea of what a region is, not just the resolution.

## Consequences

- Region counts differ between the four, so a separate model is trained per atlas. See 0004.
- Attribution must map onto four different label sets in FYP-II.
- Every run in the reliability grid is multiplied by four.

## To confirm

- [ ] Record the exact region count for each atlas from the downloaded files.
- [ ] Confirm each derivative key resolves to a `.1D` file.
