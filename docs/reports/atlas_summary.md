# Atlas Download Summary

> **SUPERSEDED (Week 1 record).** This summary describes the Week 1 download of
> 2 October: the **871** participants who passed the rater checks, before the head motion
> gate (memo 0003) was closed on 6 October. It is kept unchanged because it closed memo 0001.
> **Current figures:** QC cohort **861** (`data/splits/qc_cohort.csv`); per-atlas
> participants, nodes, edges and flat regions (Harvard-Oxford **198**, not 201) in
> `docs/reports/connectome_summary.md`. Re-running `scripts/04_fetch_all_atlases.py`
> rewrites this file and drops this note.

**Generated:** 2026-10-02  
**Pipeline:** cpac  **Strategy:** filt_global  
**Quality filter:** nilearn `quality_checked=True`, all five rater columns  
**nilearn version:** 0.14.1

This file closes the open items in `docs/decisions/0001-atlas-selection.md`.

## Per atlas

| Atlas | Family | Participants | Regions (nodes) | Timepoints min / median / max | With zero-variance regions | Invalid matrices | Size on disk |
|---|---|---|---|---|---|---|---|
| AAL | anatomical | 871 | 116 | 78 / 176 / 316 | 54 | 0 | 193.1 MB |
| CC200 | functional | 871 | 200 | 78 / 176 / 316 | 15 | 0 | 337.9 MB |
| Harvard-Oxford | probabilistic | 871 | 111 | 78 / 176 / 316 | 201 | 0 | 185.0 MB |
| Dosenbach 160 | meta-analytic | 871 | 161 | 78 / 176 / 316 | 46 | 0 | 276.1 MB |

## Checks

- Same participant set across all four atlases: **yes**
- Total size on disk: **992.1 MB**
- Invalid matrices across all atlases: **0**

## Notes for the connectome engine

- **Regions** is the number of graph nodes, and so the model's input dimension. It differs per atlas, which is why decision 0004 trains one model per atlas.
- **Zero-variance regions** produce NaN rows and columns in the correlation matrix. They are counted as valid here because the NaNs are fully explained, but the connectome engine must decide how to handle them before any model is trained. That decision needs its own memo.
- **Timepoints** vary because sites used different scan lengths and repetition times. Correlation is computed per participant, so the matrices are comparable even when the time series lengths are not.
