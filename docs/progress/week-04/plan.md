# Week 4 plan
**Dates:** Monday 19 October to Sunday 25 October 2026
**Goal of the week:** defend the midterm, then open the production track.
**Source:** FYP-I Final Work Plan, Section 4 (Week 4) and Section 8 (decisions to close).

Monday and Tuesday: all three freeze and rehearse the midterm (deck V1.5, board items
#22, #30, #36, #37, two rehearsals, fallback demo). Wednesday 21 October: midterm defence.
Thursday stand-up: every jury comment becomes a board issue with an owner. Tasks below run
Thursday to Sunday.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | With Alishba, open the Weeks 4 to 8 backlog on the board. Fixture dataset and fixture mode (memo 0014). Draft memos 0011 (tuning protocol, frozen-set re-measurement) and 0013 (analysis log, API contract). Clean-up: note in memo 0006 on Week 1 figures; "superseded" header on `atlas_summary.md`; README's accuracy claim replaced with cited figures. | The existing API runs on fixture data locally and in CI; memos 0011, 0013, 0014 in the repository |
| **Laiba** | CPU inference on the Mac (`requirements-model.txt`, CC200 checkpoint from Kaggle, same `predict()` result, documented in `SETUP.md`). Out-of-fold probabilities from cross-validation. Baseline cross-validation for AAL, Harvard-Oxford, Dosenbach 160 (no frozen measurement). Memos 0009 and 0010. | `predict()` runs on the Mac; three baseline CV runs logged |
| **Alishba** | Dashboard skeleton in `dashboard/` (memo 0012). CI: frontend job and CPU PyTorch job, with Laiba. Memo 0012. ER diagram and `database_schema.puml` with `stage` and `repeat_frozen_measurement`. Start `docs/progress/meetings.md`. | Dashboard skeleton builds in CI; meeting log started |

## Gate

- [ ] Midterm defended; jury comments logged as issues
- [ ] The full Weeks 4 to 8 backlog is on the board, assigned
- [ ] Memos 0009 to 0014 drafted
- [ ] The existing API runs on fixture data
- [ ] `predict()` runs on the Mac with the CC200 checkpoint
- [ ] Baseline cross-validation logged for the three remaining atlases
- [ ] Dashboard skeleton builds in CI; the PyTorch job runs the model tests

## Interfaces agreed this week

| Contract | Producer | Consumer | Where |
|---|---|---|---|
| Fixture mode, `NGX_DATA=fixtures` | Aleesha | Alishba (dashboard), CI, Laiba (API tests) | memo 0014, `src/neurographx/datasource.py` |
| Analysis record, endpoints, error contract | Aleesha, Laiba | Alishba | memo 0013 (frozen from the Week 5 Thursday stand-up) |
| Tuning grid, selection rule, freeze date | Aleesha | Laiba | memo 0011 |
