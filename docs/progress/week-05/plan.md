# Week 5 plan
**Dates:** Monday 26 October to Sunday 1 November 2026
**Goal of the week:** the backend is complete and tuning is under way.
**Source:** FYP-I Final Work Plan, Section 4 (Week 5); board items W5-01 to W5-18.

Thursday 29 October stand-up: memos 0009 to 0014 reviewed and accepted (W5-01); the API
contract in memo 0013 is frozen from then on.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | Memo 0013 revised to match memo 0012 (no CORS rule; Vite proxy). W5-04 shared error contract. W5-03 participant filters, with quality status read from the committed QC outputs. W5-02 `GET /atlases`, `GET /cohort/summary`, `GET /exclusions`. W5-05 analysis log writer. W5-06 analysis log in SQLite. W5-07 `GET /analyses`, `GET /analyses/{analysis_id}`. W5-08 API tests on fixture data. W5-17 manual test template and first ten cases (with Alishba). W5-R3 plan, log, CHANGELOG, merge | Every data-side endpoint passes its tests on fixture data in CI; analysis records written by the writer are visible through `GET /analyses` and in the rebuilt database |
| **Laiba** | Week 4 carry-over (Mac inference, out-of-fold probabilities, baseline CV for three atlases, memos 0009 and 0010). W5-09 `POST /analyses`, W5-10 model endpoints, W5-11 their tests. W5-12 tuning per memo 0011. W5-13 calibration module | Tuning runs logged for all four atlases; calibration merged with tests |
| **Alishba** | W5-14 Participants page, W5-15 Analysis page, W5-16 frontend unit tests, W5-17 with Aleesha, W5-18 React or Streamlit decision on 1 November, W5-R1 supervisor meeting, W5-R2 board screenshot | The dashboard lists participants and runs an analysis in fixture mode |

## Gate (FYP-I Final Work Plan, Week 5)

- [ ] Every FYP-I endpoint exists and passes its API tests on fixture data
- [ ] Analysis records are written, visible through `GET /analyses` and in the rebuilt SQLite database
- [ ] Tuning runs logged for all four atlases
- [ ] Calibration code merged with tests
- [ ] The dashboard lists participants and runs an analysis in fixture mode

## Interfaces agreed this week

| Contract | Producer | Consumer | Where |
|---|---|---|---|
| Data-side endpoints and response shapes | Aleesha | Alishba | memo 0013 part 3, `src/neurographx/api/schemas.py`, `/docs` |
| Order of checks and errors for `POST /analyses` | Aleesha | Laiba | `api/analysis_checks.check_request`, memo 0013 part 4 |
| Writing an analysis record | Aleesha | Laiba (`POST /analyses`), Aleesha (Week 6 regenerate) | `neurographx.analysis_log.log_prediction` |
| Dashboard reaches the API through the Vite proxy | Alishba | Aleesha, Laiba | memo 0012; memo 0013 part 5 |
