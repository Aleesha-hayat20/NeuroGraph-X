# Week 7 plan
**Work plan dates:** Monday 9 November to Sunday 15 November 2026. Started on Tuesday
17 November, after Week 6 closed.
**Goal of the week:** feature complete, tested, and documented in draft.
**Source:** FYP-I Final Work Plan, Section 4 (Week 7).

Sunday 15 November: feature freeze (work plan). Changes after it are bug fixes, tests and
documentation; memo 0015 adds no FYP-I feature.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | Reliability engine skeleton (work plan Section 10, item 6; memo 0016): job manifest (axis, value, atlas, seed), resumable runner that logs `stage: "variant"` runs, tests on the synthetic fixture grid; no ABIDE reliability result in FYP-I (#131). Manual test round 1 on the API and data flows built by Laiba and Alishba: API checks AC-01 to AC-08 and AC-11 to AC-14, and the dashboard cases TC-01 to TC-10 (`docs/testing/manual_tests.md`); results in `docs/testing/round_1.md` (#132). Report chapters 4.1 (data acquisition and quality control), 4.2 (connectome engine), 5.1 to 5.4 (testing) (#134, #135); test plan `docs/testing/test_plan.md` (#136). Jury remark issue numbers in the memo and logs; plan, log, CHANGELOG, merge | The reliability skeleton is merged with its tests passing in CI; round 1 API checks are logged |
| **Laiba** | Performance and robustness tests: analysis time on the Mac's CPU, repeated requests, every failure path returning the documented error (#139, #140). API reference exported to `docs/api.md` (#141). Model cards final (#144). Report chapters 4.3 to 4.5 and 5.5 to 5.8 (#142, #143). Round 1 cross-test of regenerate and export (AC-09, AC-10), which Aleesha built | Tests merged; `docs/api.md` committed; round 1 checks logged |
| **Alishba** | Remaining dashboard features: cohort overview with charts (#146), export buttons and regenerate with the "identical" indicator (#147), loading, error and empty states, the research-use notice on every page, Explanation and Reliability tabs marked "FYP-II" (#148), the development-pool note (TC-04b). Consistency pass against the mockups (#149). A "Bugs" column on the board and the fixes for round 1 bugs (#150); the dashboard cases are run by Aleesha, since each case is run by someone who did not build the feature. Report chapters 2.5, 3 and 4.6, user manual first draft (#151, #152). Diagrams final, with the jury remarks on figure order and class diagram notation (#153, #163, #164); the ER diagram image re-rendered from `docs/design/database_schema.puml`. Supervisor meeting log and Sunday board screenshot (#155, #156) | Every FYP-I use case works in the dashboard; round 1 bugs triaged |

## Gate (FYP-I Final Work Plan, Week 7)

- [ ] Every FYP-I use case on the final use case diagram works in the dashboard
- [ ] Manual test round 1 executed and logged; every bug triaged
- [ ] Reliability skeleton merged with tests on a synthetic grid
- [ ] All report chapters drafted

## Interfaces agreed this week

| Contract | Producer | Consumer | Where |
|---|---|---|---|
| Variant run record: `stage: "variant"` and the `reliability` object | Aleesha | FYP-II reliability envelope, the database | memo 0016, Section 4; `db/schema.sql` |
| Grid definition (YAML) and manifest | Aleesha | FYP-II ABIDE grid | memo 0016, Section 3; `configs/reliability/fixture_grid.yaml` |
| API checks AC-01 to AC-14 | Aleesha | Laiba (cross-test of AC-09 and AC-10) | `docs/testing/manual_tests.md` |
