# Changelog

What changed on `main`, week by week. Each week's work is merged from its own branch once
that week's tasks run (work plan Section 3, branch rule). Releases are tagged as in work plan
Section 8.8: `v1.0-fyp1` for the FYP-I final, hotfixes as `v1.0.1-fyp1`.

## [Unreleased]

### Week 8 (work plan 16 to 22 November 2026)
- Release checklist, `docs/release/checklist.md` (#174): what must be true on `main`, in CI
  and on the demonstration machine before `v1.0-fyp1` is tagged, and the hotfix route
  during the evaluation window.
- `SETUP.md` rewritten for the clean-clone test (#137, #177): a fresh clone to a running
  dashboard in fixture mode, then the real data (downloaded or copied), the integrity check,
  a CPU prediction, the checks CI runs, and the common problems. README: quick start with
  the repository address, a documentation table, and the full error list.
- The API loads the model code at start-up, so the first analysis after the server starts
  no longer pays about 4.5 seconds of library loading (#139 follow-up;
  `tests/test_performance.py`). `scripts/benchmark_api.py` starts the server the same way
  and reports the start-up time.
- A connectome with missing or infinite values is refused by `POST /analyses` and by
  regenerate with 503 and its own sentence, instead of a sentence that blamed the model;
  `inference.NonFiniteGraph`. Two cases added to `tests/test_robustness.py`, closing the
  "NaN graph" path of the work plan's robustness list (#140 follow-up).
- Version 1.0.0 in the package, the API (`GET /health`) and the dashboard, for `v1.0-fyp1`.
- Round 1 report: the plan for round 2 states the swapped testers and that AC-09 and AC-10
  passed.

### Week 7 (work plan 9 to 15 November 2026; started 17 November)
- Merged on 22 November: round 1 cross-test of regenerate (AC-09) and export (AC-10) on
  real data, both passed, so all 14 API checks passed (PR #201); dashboard fixes for the
  round 1 bugs, the development-pool note (#198), atlases without a model or data disabled
  (#199) and the majority-class baseline on the Models page (#200) (PR #203); the database
  schema image re-rendered with the `reliability` column and the `variant` stage (#153,
  PR #204).
- Merged in Week 8 (PR #202): robustness tests, every failure path returning its
  documented status and one sentence with nothing written to the analysis log
  (`tests/test_robustness.py`, #140); Starlette's bare 404 and 405 and a body that is not
  JSON now answer with one plain sentence too (`api/errors.py`). Performance benchmark and
  tests (`scripts/benchmark_api.py`, `tests/test_performance.py`,
  `docs/reports/performance.md`, #139). API reference `docs/api.md` (#141). Final model
  cards, the CC200 card reporting both frozen-set measurements and why run `cf60f29e` is
  served (#144).
- Reliability engine skeleton (M5, memo 0016; #131): `neurographx.m5_reliability` and
  `scripts/run_reliability.py`. A grid definition (`configs/reliability/fixture_grid.yaml`)
  is expanded into a job manifest of axis, value, atlas and seed, written once; a resumable
  runner trains and scores each job on the development pool and logs it with
  `"stage": "variant"` and a `reliability` object. Axes: atlas, seed, resample (stratified
  bootstrap, scored out of bag) and site (left out). Real ABIDE data is refused without
  `--allow-real-data`; no ABIDE reliability result is produced in FYP-I.
- Database schema: `stage` accepts `variant`; new `reliability` column (JSON). ER diagram
  source updated. Run-log schema version unchanged (3).
- `tests/test_reliability.py`: 30 tests on the fixture grid of 16 jobs (manifest, splits,
  resuming after a stop, guards, database import, and the real GCN giving identical
  predictions on a repeated job).
- Manual tests: API checks AC-01 to AC-14 added to `docs/testing/manual_tests.md`; TC-09
  points to `docs/model_cards/`. Test plan `docs/testing/test_plan.md` (#136).
- Manual test round 1 (`docs/testing/round_1.md`, #132), 20 November, build `04f01b9`:
  12 API checks passed, AC-09 and AC-10 not run (cross-test pending); dashboard cases 8
  passed, 2 failed, 1 blocked; bugs #198, #199 and #200.
- Week 7 log.
- README: reliability engine section.
- The jury remark issues (#162, #163, #164) are named in memo 0015, the jury remarks page,
  the Week 4 log and this changelog.

### Midterm jury remarks and memo 0015 (17 November 2026)
- The three written remarks of the midterm jury, released on 17 November, logged as issues
  with owners (#162, #163, #164; board task #44) and recorded in
  `docs/progress/midterm_jury_remarks.md`.
- Memo 0015, real-world repositioning, approved by the supervisor on 17 November: the same
  disorder, data, models and modules, with a named user (research groups and hospital
  research units with their own resting-state fMRI). FYP-II opens the system to uploaded
  data, with a data compatibility check and per-result reliability. No FYP-I feature or
  result changes.
- README: "Who it is for". SRS version 1.2: product scope and references point to memo
  0015; no requirement changed. Report outline: intended users in Chapter 1; Chapter 6
  takes the FYP-II future work from memo 0015.

### Week 6 (2 to 8 November 2026)
- Regenerate and export (memo 0013, part 3; W6-06, W6-07):
  `POST /analyses/{analysis_id}/regenerate` re-runs a past analysis with the model of its
  original training run, records the repeat with `reproduces_analysis_id` and reports
  whether the result is identical; `GET /analyses/{analysis_id}/export` returns the record
  as `analysis_<id>.json` or `.csv`. `inference.predict` and `load_model` accept an explicit
  run entry, and POST /analyses and regenerate share one graph builder, so both go through
  the same code.
- Integrity check, `scripts/check_integrity.py` (`neurographx.integrity`): run log, registry,
  checkpoints and their hashes, split, out-of-fold and frozen-prediction files, calibration
  files, cohort partition, connectome store and analysis log; a replay of each registered
  model on its saved frozen-set predictions confirms the models get the same inputs from a
  store built on another machine. New CI step on the fixture dataset; `make integrity`.
- Confound check, `scripts/confound_check.py` (`neurographx.m3_model.confounds`):
  out-of-fold accuracy by site, by motion quartile and with flat regions, written to
  `docs/reports/confound_check.md` as a limitation analysis; `make confounds`.
- The API smoke test also runs, regenerates and exports one analysis on the fixture data.
- `.gitattributes`: text files use LF line endings on every platform.
- Report v2.0 structure, chapter owners (work plan Section 9), formatting and schedule in
  `docs/report/README.md`, and the software requirements specification,
  `docs/report/srs.md` (version 1.1).
- Memos 0010, 0011, 0013 and 0014 marked accepted (29 October) and memo 0009 accepted with
  option A (12 November); their open items closed.
- Progress logs of Weeks 1, 2, 4 and 5 completed from the records.
- Laiba's Week 6 work (PR #126): `POST /analyses`, calibration (Platt scaling on
  out-of-fold probabilities), the four final models measured once on the frozen set, model
  cards and the results table.
- Alishba's Week 6 work: History page (PR #124), supervisor meetings log (PR #125), unit
  tests for the result card and History page (PR #127), Models page with reliability
  diagrams (PR #128), and the Playwright end-to-end test in CI (PR #129).

### Week 5 (26 October to 1 November 2026)
- API error contract: every error is `{"detail": "<plain sentence>"}` with 404, 409, 422 or
  503; FastAPI's validation errors are turned into one sentence (memo 0013 part 4).
- Participants: quality status, first gate and reasons now come from the committed QC
  outputs, so the completeness gate is included; new `exclusion_gate` and `split` fields;
  filters `site`, `group` and `qc_status`.
- New endpoints: `GET /atlases`, `GET /cohort/summary`, `GET /exclusions`, `GET /analyses`,
  `GET /analyses/{analysis_id}`.
- Analysis log: `neurographx.analysis_log` writes validated, append-only records to
  `runs/analysis_log.jsonl`; `scripts/build_db.py` loads them into SQLite.
- Order of checks for `POST /analyses` in `api/analysis_checks.py`.
- Fixture dataset: a completeness case (generator 1.1.0); 17 retained, 7 excluded.
- Memo 0013 revised (Vite proxy, no CORS rule); memo 0014 amended.
- Manual test template and cases TC-01 to TC-10 (`docs/testing/manual_tests.md`).
- Dashboard scaffold: React and Vite in `dashboard/`, routing, seven placeholder pages, one
  API client module and the Vite proxy (memo 0012, W4-19; PR #88).
- `.gitattributes`: append-only logs merge with `union`.
- Dashboard: fixture-data banner and data mode in the footer (PR #90); ER diagram with `stage`
  and `repeat_frozen_measurement` (PR #91); CI frontend job (PR #89) and CPU-only PyTorch with
  coverage (PR #92); Participants page with filters, quality badge and Run (PR #117).
- Laiba's Week 4 work (PR #93): CPU inference check
  (`scripts/predict_one.py`), checkpoints resolved against the data root (memo 0009),
  out-of-fold probabilities from cross-validation, baseline CV for AAL, Harvard-Oxford and
  Dosenbach 160, memos 0009 and 0010 proposed.
- Laiba's Week 5 work (PR #94): memo 0011 tuning grid (48 CV runs, frozen
  set not read), class-weighted loss, selection (`docs/reports/tuning_selection.md`), run-log
  schema 3 (`repeat_reason`, `checkpoint_sha256`).
- Laiba's model endpoints (PR #118, W5-10): `GET /models` and `GET /models/{atlas}` in
  `api/models.py`, with the registry entry, training settings, checkpoint presence and
  calibration when it exists.
- Fixture generator 1.2.0: schema 3 run log, out-of-fold and frozen prediction files.
  `tests/test_api_models.py` now reads the fixture's run ID from its registry instead of
  pinning it, because the ID changes whenever the fixture is rebuilt.

### Week 4 (19 to 25 October 2026)
- Fixture dataset in the real file formats and fixture mode, `NGX_DATA=fixtures`
  (memo 0014); CI smoke test of the API on the fixture (PR #87).
- Memos 0011 (tuning protocol and frozen-set re-measurement) and 0013 (analysis log and API
  contract) drafted (PR #87); memo 0012, dashboard stack, accepted (PR #86).
- PyTorch and PyTorch Geometric pinned in `requirements.txt` (PR #38).
- Clean-up: Week 1 figures noted in memo 0006; `atlas_summary.md` marked superseded; README
  accuracy claim replaced with cited figures (PR #87).

### Weeks 2 and 3 (5 to 18 October 2026)
- Quality control closed (memo 0003): cohort of 861, exclusion log (PR #33).
- Connectome engine for four atlases (memo 0007); frozen evaluation set of 100 and five
  development folds (memo 0005); leakage test; independent verification of 80 matrices
  (PR #33).
- Run logging, inference path, database schema and the first API endpoints (PRs #29 to #32).
- CC200 baseline: 5-fold cross-validation and one frozen-set measurement; model registered
  (PRs #34 and #35).

### Week 1 (28 September to 4 October 2026)
- Repository scaffold, CI, decision memos 0001 to 0005.
- Phenotypic download, metadata report, pilot atlas, four atlases downloaded (PR #25).
- Training environment and the synthetic brain-graph test (PRs #26 to #28).
