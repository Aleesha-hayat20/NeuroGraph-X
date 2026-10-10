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

## To confirm (closed 2026-10-02)

Source: `docs/reports/atlas_summary.md`, generated 2026-10-02 by
`scripts/04_fetch_all_atlases.py` (pipeline `cpac`, strategy `filt_global`).

- [x] Record the exact region count for each atlas from the downloaded files.
  AAL **116**, CC200 **200**, Harvard-Oxford **111**, Dosenbach 160 **161** (see note below).
- [x] Confirm each derivative key resolves to a `.1D` file.
  All four downloaded as `.1D` text files for the same **871** participants, and all
  3,484 matrices (871 x 4) passed the validity checks. Total size on disk 992.1 MB.
- [x] Note any atlas where some participants have regions with zero variance.
  Participants with at least one flat region: AAL 54, CC200 15, Harvard-Oxford 201,
  Dosenbach 160 46 (out of 871 each). Handling goes in its own memo before training.

**Open note, Dosenbach 160 has 161 columns.** The atlas is named for 160 regions but the
files have 161 columns. Checked 2026-10-06: the header labels run `#1` to `#160`
contiguously, and the 161st column is labelled `#223`. The file itself does not say what
label 223 refers to, so this is recorded as an observation, not explained. Across the 871
participants, column 161 is flat in none of them (the most often flat columns are 150 and
154, 22 participants each). The connectome engine keeps all 161 columns as nodes. If the
source of label 223 is confirmed later, record it here and, if it should be dropped, do
it through a new memo so the change is declared.