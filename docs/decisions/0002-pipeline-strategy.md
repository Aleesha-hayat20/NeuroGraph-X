# 0002. Preprocessing pipeline and strategy

**Status:** Accepted
**Date:** 2026-09-28, accepted 2026-10-01
**Owner:** Aleesha Hayat

## Context

ABIDE Preprocessed offers four pipelines (CCS, CPAC, DPARSF, NIAK), each with four
strategies covering band-pass filtering on or off and global signal regression on or off.
That is sixteen versions of the dataset. The choice changes results.

## Decision

Fix one pipeline and one strategy for the whole project and declare it in `configs/data.yaml`.

Final: **CPAC**, strategy **filt_global** (band-pass filtering on, global signal regression on).

## Rationale

The pipeline is not varied because the compute cost of a fifth axis is multiplicative and
outside the FYP-I and FYP-II budget. Fixing it and stating it openly is the honest option.

## Confirmation (closed 2026-10-01)

- [x] Identify which pipeline and strategy the baseline papers we compare against used.
  Our primary comparator is Heinsfeld et al. (2018), the canonical deep learning result on
  ABIDE that later graph neural network papers benchmark against. Its methods section
  states: C-PAC preprocessing, band-pass filtering at 0.01 to 0.1 Hz, the global signal
  included as a nuisance regressor, the CC200 atlas, and 505 autism plus 530 control
  participants.
- [x] Match that choice so the numbers mean the same thing. C-PAC with band-pass and
  global signal regression is exactly `cpac` / `filt_global`, which is what
  `configs/data.yaml` already declares. No change was needed.
- [x] Record the check here with the reference.

Reference: Heinsfeld, A. S., Franco, A. R., Craddock, R. C., Buchweitz, A., and
Meneguzzi, F. (2018). Identification of autism spectrum disorder using deep learning and
the ABIDE dataset. *NeuroImage: Clinical*, 17, 16 to 23.
PubMed: https://pubmed.ncbi.nlm.nih.gov/29034163/

**When another comparator is added** (for example a graph neural network paper in the
literature table), check its preprocessing the same way and note it below. If it used a
different strategy, say so next to its numbers rather than changing ours.

| Comparator | Pipeline | Strategy | Atlas | Matches ours |
|---|---|---|---|---|
| Heinsfeld et al. 2018 | C-PAC | band-pass + GSR (filt_global) | CC200 | Yes |

## Consequences

- The strategy decides which version of the files is downloaded, so it had to be fixed
  before the full four atlas download. It now is.
- Pipeline variability becomes a stated limitation rather than a measured axis.
- A jury question about it has a prepared answer: it is a legitimate fifth axis, the cost
  is multiplicative, and the choice is declared rather than hidden.
