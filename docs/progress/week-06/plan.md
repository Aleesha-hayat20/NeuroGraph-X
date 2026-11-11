# Week 6 plan
**Dates:** Monday 2 November to Sunday 8 November 2026
**Goal of the week:** four calibrated final models, and the dashboard working end to end on
real data.
**Source:** FYP-I Final Work Plan, Section 4 (Week 6).

Monday 2 November: tuning freeze (memo 0011). After this, no setting changes.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | W6-06 regenerate, W6-07 export (memo 0013, part 3). Integrity check `scripts/check_integrity.py`, in CI on the fixtures and on the real data. Confound check on the out-of-fold predictions, `docs/reports/confound_check.md`. With all: report skeleton and SRS. Memo 0009 decision; plan, log, CHANGELOG, merge | Regenerate reports "identical"; the integrity check passes in CI and on the real data |
| **Laiba** | `POST /analyses` (W5-09, carried). Select each atlas's configuration (memo 0011); train the four final models on the 761 development participants; fit calibration on out-of-fold probabilities (W6-04); measure each once on the frozen set, CC200 as a declared repeat. Register them; commit the checkpoints per memo 0009. Model cards in `docs/model_cards/` | Four calibrated models registered, checkpoints committed with their hashes |
| **Alishba** | Dashboard on the live API with real data. W6-11 Models page, W6-12 History page. W6-13 end-to-end test (Playwright) in CI on fixtures. Diagrams to the as-built system (architecture, DFD level 1, class or component diagram, sequence diagram for regenerate). W6-R1 supervisor meeting log | The end-to-end test passes in CI |
| **All three** | `docs/report/` with the Report v2.0 structure and chapter owners (Section 9); SRS v1.1 matching the built endpoints | Both committed |

## Gate (FYP-I Final Work Plan, Week 6)

- [x] Four calibrated models registered, checkpoints committed, hashes recorded
- [x] Each atlas's frozen set measured once after the tuning freeze, CC200 recorded as a declared repeat
- [x] The dashboard runs an analysis end to end on real data
- [x] The integrity check passes in CI and on the real data
- [x] The end-to-end test passes in CI
- [x] Report skeleton and SRS v1.1 committed

## Interfaces agreed this week

| Contract | Producer | Consumer | Where |
|---|---|---|---|
| Regenerate response `{analysis, original, identical, differences}` | Aleesha | Alishba (Week 7 regenerate control) | memo 0013 part 3, `RegenerateResult` in `src/neurographx/api/schemas.py` |
| Export file names and CSV layout | Aleesha | Alishba (Week 7 export buttons) | memo 0013 part 3, `src/neurographx/api/reproduce.py` |
| Checkpoints in git, one `.gitignore` exception each | Laiba | everyone, the integrity check | memo 0009, acceptance of 12 November |
