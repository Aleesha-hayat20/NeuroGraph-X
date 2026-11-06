# Changelog

What changed on `main`, week by week. Each week's work is merged from its own branch once
that week's tasks run (work plan Section 3, branch rule). Releases are tagged as in work plan
Section 8.8: `v1.0-fyp1` for the FYP-I final, hotfixes as `v1.0.1-fyp1`.

## [Unreleased]

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
