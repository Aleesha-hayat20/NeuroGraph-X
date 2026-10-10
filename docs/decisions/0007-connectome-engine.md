# 0007. Connectome engine: measure, Fisher transform, storage, caching, flat regions

**Status:** Accepted for storage and transform. Flat-region fill for training: Proposed,
needs Laiba's agreement as the consumer.
**Date:** 2026-10-06
**Owner:** Aleesha Hayat
**Related:** 0002 (pipeline), 0004 (one model per atlas), 0006 (baseline model architecture)

Numbered 0007 because Laiba's model architecture memo took 0006 while this was in review.

## Context

Every model, every reliability run and every dashboard view reads the same connectivity
matrices. If they were computed differently in different places, results would not be
comparable. Week 1 left one question open: regions with a flat signal (zero variance)
give empty (NaN) rows in the correlation matrix (`docs/reports/atlas_summary.md`).

## Decision

| Choice | Decision | Why |
|---|---|---|
| Connectivity measure | Pearson correlation between region time series | The standard functional connectivity measure, and the one our primary comparator used (memo 0002) |
| Transform | Fisher z = arctanh(r) = 0.5 ln((1 + r) / (1 - r)) | r is squashed near plus and minus one; z is close to normally distributed, so averages and differences behave |
| Clipping | abs(r) clipped to 0.9999999 before the transform | arctanh(1) is infinite; the clip keeps z finite (at most about 8.4) |
| Diagonal | r diagonal = 1, z diagonal = 0 | A region with itself carries no information; 0 avoids an infinite value |
| Storage | One `.npz` per atlas: strict upper triangle of r and z, float32, plus a zero-variance mask, timepoint counts and participant ids; a `.json` manifest beside it | The matrix is symmetric, so the upper triangle holds everything and halves the size. float32 keeps about seven significant digits, far below any effect we measure. 315 MB for all four atlases |
| Location | `data/processed/connectomes/cpac_filt_global/` | Not committed; rebuilt in under a minute by `scripts/07_build_connectomes.py` |
| Caching | SHA-256 fingerprint of engine version, parameters, participant order and the contents of every input file. Same fingerprint and an intact output file means reuse | Re-running is instant, and any change to any input forces a rebuild instead of silently serving stale matrices |
| Flat regions on disk | Kept as NaN, with a boolean mask | Storage records what the data is; filling is a modelling choice and stays visible |

## Flat regions in training (Proposed)

`ConnectomeSet.matrix(..., fill_nan=0.0)` and `stack(..., fill_nan=0.0)` replace NaN with 0,
meaning "no connection measured". Proposed default for the GNN: fill with 0 and keep the
mask available as a node feature if useful. Affected participants per atlas (QC cohort of
861): AAL 54, CC200 15, Harvard-Oxford 198, Dosenbach 160 46. Dropping those participants
instead would cost 23 per cent of the Harvard-Oxford cohort, which is why it is not the
default. Laiba confirms or amends this before the first training run, and the choice is
recorded here. Memo 0006 (model architecture) says the graph builder raises on any NaN
rather than repairing silently; that stays correct, because with this policy the fill
happens explicitly in the loader call (`fill_nan=0.0`), where it is visible and logged in
the run configuration.

Matches memo 0006 on the rest of the interface: node features are rows of the Fisher z
matrix, and the engine supplies unthresholded matrices with the z diagonal set to 0.
Thresholding stays in the model code.

## Verification

`scripts/08_verify_connectomes.py` recomputes 20 random participants per atlas by routes
that share no code with the engine (pandas reader, Pearson written out by hand,
`scipy.stats.pearsonr` on sampled pairs, nilearn `ConnectivityMeasure` with the empirical
covariance, Fisher written out as a logarithm). All 80 agreed to within float32 rounding
on 2026-10-06. Report: `docs/reports/connectome_verification.md`.

Note for anyone using nilearn directly: `ConnectivityMeasure(kind="correlation")` uses
Ledoit-Wolf shrinkage by default, which is not plain Pearson correlation. Pass
`cov_estimator=EmpiricalCovariance()` to match the engine.

## Interface (the graph object contract, agreed 2 October)

```python
from neurographx.m2_connectome.engine import atlas_paths, load_atlas
npz, manifest = atlas_paths("data/processed/connectomes", "cpac", "filt_global", "rois_cc200")
cset = load_atlas(npz, manifest)
cset.atlas_key, cset.n_regions          # atlas identifier and node count
cset.matrix("NYU_0050952", kind="z", fill_nan=0.0)   # (200, 200) adjacency for one participant
cset.stack("z", fill_nan=0.0, participants=train_ids)  # (n, 200, 200)
```

## Consequences

- One stored file per atlas, so the per-atlas models (memo 0004) each read one file.
- Any change to the measure, clip or dtype changes the fingerprint and rebuilds everything.
- The engine version is written into every manifest, so a checkpoint can record exactly
  which matrices it was trained on.
