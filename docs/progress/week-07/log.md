# Week 7 log

Work plan dates 9 to 15 November 2026; the week's work started on 17 November, after Week 6
closed.

## Entries

### 17 November (Alishba): remaining dashboard features
Merged on 19 November in PRs #166 to #169.
- **Overview page (#146, PR #166):** cohort totals, the excluded count by first gate failed,
  the included count by split, and bar charts by group and by site, all from
  `GET /cohort/summary`.
- **FYP-II tabs and About page (#148, PR #167):** Explanation and Reliability tabs marked as
  FYP-II features; an About page with the version, the team and the research-use statement.
- **Export and regenerate in History (#147, PR #168):** Export JSON and Export CSV buttons
  for an analysis record, and Regenerate with the "Identical to the original" message, the
  original and the new result side by side, and a link to the new analysis.
- **Consistency pass (#149, PR #169):** the same atlas names, time and count formats on
  every page; "included" instead of "retained" on Overview.
- Dashboard tests: 50 passed in 10 files; lint clean.

### 17 to 20 November (Aleesha): reliability engine skeleton, manual test round 1, test plan
- **Reliability engine skeleton (#131, memo 0016).** `neurographx.m5_reliability` and
  `scripts/run_reliability.py`. A grid definition in `configs/reliability/` is expanded into
  a job manifest, written once, whose jobs carry an axis, a value, an atlas and a seed. Four
  axes: atlas (the reference run), seed, resample (a stratified bootstrap of the development
  pool, scored on the participants it left out) and site (one site left out of training and
  scored). Every variant trains for a fixed number of epochs, so no epoch is chosen on the
  participants it is scored on. Each finished job is logged with `"stage": "variant"` and a
  `reliability` object (grid, manifest, job, axis, value); a run that stops resumes with the
  same command and skips every logged job. Real ABIDE data is refused without
  `--allow-real-data`, the output may not lie inside `fixtures/`, and the leakage check runs
  before the first job. No ABIDE reliability result is produced in FYP-I, following the
  supervisor's direction to deliver the finding in FYP-II.
- **Fixture grid** (`configs/reliability/fixture_grid.yaml`): two atlases, the reference
  run, two seeds, two bootstraps and each of the three synthetic sites left out, 16 jobs.
  On the Mac, a run stopped after 4 jobs resumed with the remaining 12, and a third run had
  nothing left to do.
- **Database schema:** `stage` accepts `variant`; new `reliability` column (JSON). The
  run-log schema version stays 3.
- **Tests:** `tests/test_reliability.py`, 30 tests (manifest, splits, resuming, guards,
  database import, and the real GCN giving identical predictions on a repeated job).
  Python suite `420 passed`; ruff clean.
- **Manual test round 1 (#132), 20 November, build `04f01b9`:** API checks AC-01 to AC-14
  added to `docs/testing/manual_tests.md`. Twelve API checks passed; AC-09 and AC-10 are
  Laiba's cross-test of regenerate and export and were not run in this round. Dashboard
  cases: eight passed, TC-05 and TC-09 failed, TC-04b blocked. Bugs #198, #199 and #200
  filed for Alishba. Results in `docs/testing/round_1.md`.
- **Test plan (#136):** `docs/testing/test_plan.md`, the seven test levels and the rules the
  tests enforce.
- **Report:** sections 4.1, 4.2 and 5.1 to 5.4 drafted for the team's report document.
- **Jury remarks:** issues #162, #163 and #164 named in memo 0015, the jury remarks page, the
  Week 4 log and the CHANGELOG.

## Decisions taken
- `docs/decisions/0016-reliability-engine-skeleton.md` proposed on 17 November: four axes,
  fixed epochs, an immutable manifest per grid name, the variant run-log record, and the
  real-data guard.
- The dashboard cases of round 1 are run by Aleesha, since Alishba built the pages; Alishba
  takes the Bugs column and the fixes (#150).

## Week close
**Planned for Sunday 15 November; closed on Friday 20 November.** The week started on
17 November, after Week 6 closed.
**Gate items:**
- Reliability skeleton merged with tests on a synthetic grid: met.
- Manual test round 1 executed and logged, every bug triaged: met; three dashboard bugs
  filed (#198 to #200).
- Every FYP-I use case works in the dashboard: not yet; the three bugs are open.
- All report chapters drafted: Aleesha's sections drafted; the others are in progress.

**Carried into next week:** bugs #198 to #200 and the Bugs column (#150), report chapters
2.5, 3 and 4.6, the user manual and the final diagrams with the ER diagram image re-rendered
for the new column (Alishba); performance and robustness tests, the API reference, report
chapters 4.3 to 4.5 and 5.5 to 5.8, the final model cards, and the AC-09 and AC-10
cross-test (Laiba); acceptance of memo 0016 (team).
