# Changelog

What changed on `main`, week by week. Each week's work is merged from its own branch once
that week's tasks run (work plan Section 3, branch rule). Releases are tagged as in work plan
Section 8.8: `v1.0-fyp1` for the FYP-I final, hotfixes as `v1.0.1-fyp1`.

## [Unreleased]

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
