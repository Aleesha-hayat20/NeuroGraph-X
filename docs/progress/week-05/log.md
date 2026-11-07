# Week 5 log

## Monday 26 October, stand-up
**Closed since last time:** Week 4 data side merged (PR #87): fixture dataset and fixture
mode, memos 0011, 0013 and 0014 drafted, clean-up. Memo 0012 merged (PR #86). Dashboard
scaffold merged (PR #88, W4-19).
**Carried into this week:** (fill in, from the Week 4 board)
**Next:** tasks in `plan.md`.
**Blocked:** (fill in)

## Thursday 29 October, stand-up
**Memos accepted (W5-01):** (fill in which of 0009 to 0014 were accepted, and any changes asked for)
**Next:** (fill in)
**Blocked:** (fill in)

## Entries

### 27 October (Aleesha)
- **Memo 0013 revised before acceptance.** Part 5 proposed a CORS rule in the API; memo 0012
  (accepted 26 October) routes the dashboard through Vite's proxy and rejects that rule.
  Part 5 now adopts the proxy; the API has no CORS middleware. Response shapes made exact
  while building them (revision notes at the end of the memo).
- **W5-04 error contract.** `src/neurographx/api/errors.py`: one helper per status
  (404, 409, 422, 503), FastAPI's validation errors turned into one plain sentence, data
  errors answered with 503, unexpected errors with a plain 500.
- **W5-03 participants.** Quality status, first gate and reasons now come from the
  committed QC outputs (`qc_cohort.csv`, `exclusion_log.csv`), so the completeness gate is
  included; new `exclusion_gate` and `split` fields. Filters `site` (any case), `group`,
  `qc_status` combine; invalid values are 422 with a plain sentence.
- **W5-02.** `GET /atlases`, `GET /cohort/summary`, `GET /exclusions`
  (`src/neurographx/api/cohort.py`).
- **Order of checks for `POST /analyses`** (memo 0013 part 4) in
  `src/neurographx/api/analysis_checks.py`, ready for Laiba's endpoint.
- **W5-05 analysis log writer** (`src/neurographx/analysis_log.py`): ten fields, validated;
  unique 12-character ids; run_id must be in the run log; reproductions must point at an
  existing analysis; append-only with a lock.
- **W5-06.** `scripts/build_db.py` rebuilds `run_log`, `model_registry` and `analysis_log`;
  `--data fixtures` builds the fixture database.
- **W5-07.** `GET /analyses` (newest first; filters; limit) and `GET /analyses/{analysis_id}`.
- **Fixture (memo 0014 amendment):** a completeness case added (participant 90012), so every
  QC gate is planted; regenerated: 17 retained, 7 excluded.
- **W5-08 tests:** `tests/test_api.py` rewritten, new `tests/test_api_data.py`,
  `tests/test_api_history.py`, `tests/test_analysis_log.py`; the live-screen agreement test
  moved to `tests/test_screening.py`. Smoke test now calls every data-side endpoint.
- **W5-17:** `docs/testing/manual_tests.md`, template and TC-01 to TC-10 (to review with
  Alishba).
- `CHANGELOG.md` started (W5-R3); `.gitattributes` with `runs/*.jsonl merge=union`.
- Tests: (paste the final `pytest` line here).
- Pull request: (paste the link).

### 6 and 7 November (Aleesha): catch-up, reviews and merges
- Repository checked: `main` at `9324ccd` (Alishba's PRs #89 to #92 and #117). Laiba's
  #93 (Week 4), #94 (Week 5, stacked on #93) and #118 (model endpoints, on `main`) merge
  into it without conflicts; with all three on `main`, 230 tests pass.
- **Fixture question answered:** nobody worked on wrong data. The fixture on `main` was
  the Week 4 version (18 retained, 6 excluded), complete and consistent; Alishba's pages
  read every number from the API; Laiba's baseline CV and tuning ran on the real data on
  Kaggle, never on the fixture. Two things followed the fixture's *format* and were
  updated here: #94 introduced run-log schema 3 and prediction files, so the generator
  moved to 1.2.0 (memo 0014 amendment); and one #118 test pinned the Week 4 fixture's run
  ID (`1a9384db`), so it now reads the ID from the fixture registry.
- **#93 checks on the Mac:** `pytest` 209 passed; the fixture example
  `NGX_DATA=fixtures python scripts/predict_one.py --participant 0090001` predicts autism
  (run `1a9384db`); real CC200 check on the CPU,
  `predict_one.py --participant 0050011 --atlas cc200 --expect control:0.7052`:
  `matches reference control:0.7052 (tolerance 0.001): True`. Checkpoint `cc200_00252f2b.pt` received from Laiba (sent as `.pt.zip`, renamed),
  SHA-256 `4adb11ca…ecc9`. ABIDE licence for memo 0009 option A: CC BY-NC-SA 3.0,
  non-commercial research use unrestricted (ABIDE I page).
- **#94 checks on the Mac:** `python scripts/select_config.py` reproduces
  `docs/reports/tuning_selection.md` exactly; all 54 out-of-fold files pass `check_oof`
  and match their recorded SHA-256; the frozen set has been measured once in total (CC200,
  `00252f2b`); every tuning run is dated before the 2 November freeze.
- **#118 checks on the Mac:** `pytest` 230 passed on `main` with #93, #94 and #118; in
  fixture mode `/models` and `/models/cc200` answer, `/models/ho` gives 503 and
  `/models/cc400` gives 422; on the real registry `/models/cc200` reports `00252f2b`.
- Tests after merging everything into the Week 5 branch and regenerating the fixture:
  `308 passed`.

### 7 November (Alishba)
- **Participants page (W5-14)** merged (PR #117). **Analysis page (W5-15)** in review
  (PR #120): participant and atlas choice, run, result card; API errors are shown as the
  API's own sentence.
- **React or Streamlit (W5-18): React kept.** All seven checks of memo 0012 (P1 to C1)
  pass on fixture data; evidence in `docs/progress/week-05/react-check/`. Decided on
  7 November, six days after the 1 November date, because the test needs both pages.
- `POST /analyses` (W5-09) is not on `main`, so A1 to A3 ran against a local stand-in that
  uses the real `check_request` and invents only the prediction. Reported as a backend
  delay; it does not count against React (memo 0012).
- The real `GET /atlases` sends `n_regions: null` for atlases without data; the page now
  leaves the region count out in that case (second commit of PR #120).
- Next: Vitest tests for both pages (W5-16, not written yet).

### 8 November (Laiba): tuning grid record, calibration, checkpoint
- **First grid run lost, re-run unchanged.** The first run of the memo 0011 grid (all 48
  CV runs, 31 October to 1 November) was in an interactive Kaggle session that ended
  before its files were downloaded, so its run log and OOF files were lost. The full grid
  was re-run unchanged (same code, settings, seed and tag `0011-v1`) as a committed Kaggle
  run on 1 November, before the 2 November freeze. Only the re-run is in the run log
  (60 lines, 54 OOF files, PR #94).
- **Were first-run results seen?** I do not remember whether I saw any of its results
  while it ran; the notebook shows progress as runs finish, so it cannot be ruled out. It
  could not affect the selection: the rule was fixed in memo 0011 before any tuning run;
  `scripts/select_config.py` computes the selection from the re-run's log alone (Aleesha
  reproduced it exactly); the re-run was not changed; neither run read the frozen set.
- **Calibration (W5-13) carried to Week 6** per memo 0010: each calibrator is fitted on
  the OOF table of the CV run its final model comes from, so it follows the final models.
  Code in PR #126 (#77).
- **Checkpoint confirmed (#93):** my `cc200_00252f2b.pt` has SHA-256 `4adb11ca…ecc9`, the
  same as the copy tested on Aleesha's Mac.
- **W5-09 `POST /analyses` (#73)** built once the analysis-log writer was merged (#119);
  in the Week 6 pull request.

## Decisions taken
- `docs/decisions/0013-analysis-log-and-api-contract.md` (revised 27 October, for acceptance)
- `docs/decisions/0014-fixture-data.md` (amended 27 October)
- `docs/decisions/0012-dashboard-stack.md` (decision of 7 November: React kept)

## Week close, Sunday 1 November
**Gate items met:**
**Gate items missed, and why:**
**React or Streamlit (W5-18):** React kept (7 November); all seven checks pass, evidence in `docs/progress/week-05/react-check/` (memo 0012).
**Carried into next week:**
**Board screenshot:** `board.png`
