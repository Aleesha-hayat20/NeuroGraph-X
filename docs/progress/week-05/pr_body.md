## What this adds (Week 5, data side)

- **Memo 0013 revised:** part 5 adopts memo 0012's Vite proxy instead of a CORS rule, so the two memos agree; response shapes made exact. **Memo 0014 amended:** a completeness case in the fixture.
- **Error contract (W5-04):** `api/errors.py`. Every error is `{"detail": "<plain sentence>"}`: 404, 409 (with the exclusion reasons), 422 (including FastAPI's own validation errors, now one sentence), 503, and a plain 500.
- **Participants (W5-03):** status, first gate and reasons from the committed QC outputs (includes the completeness gate); new `exclusion_gate` and `split`; filters `site`, `group`, `qc_status` combine.
- **New endpoints (W5-02, W5-07):** `GET /atlases`, `GET /cohort/summary`, `GET /exclusions`, `GET /analyses`, `GET /analyses/{analysis_id}`.
- **Analysis log (W5-05, W5-06):** `neurographx.analysis_log` is the only writer (validated, append-only, run_id must be logged); `scripts/build_db.py` loads it into SQLite.
- **For `POST /analyses` (Laiba, W5-09):** `api.analysis_checks.check_request` runs the five checks in memo 0013's order; then `inference.predict`, then `analysis_log.log_prediction`.
- **Manual tests (W5-17):** `docs/testing/manual_tests.md`, template and TC-01 to TC-10.
- `CHANGELOG.md`, `.gitattributes` (`runs/*.jsonl merge=union`), README API table, Makefile `db` targets.

## Merged in from `main`

Laiba's #93, #94 and #118 and Alishba's #89 to #92 and #117. To fit them together:

- **Fixture generator 1.2.0** (memo 0014 amendment): the fixture follows run-log schema 3
  and writes out-of-fold and frozen prediction files with `m3_model.oof`, like the real runs.
  Fixture regenerated: 24 participants, 17 retained, 7 excluded.
- `api/main.py`: one merge conflict with #118, resolved by keeping both sides; the
  `/models` router is included after the error handlers.
- `tests/test_api_models.py`: reads the fixture's run ID from its registry instead of the
  Week 4 value, so rebuilding the fixture never breaks it.

## For Alishba

The Participants and Analysis pages can use `GET /participants` (with filters) and `GET /atlases` in fixture mode now (`make api-fixtures`). Please review `docs/testing/manual_tests.md`.

## For Laiba

`POST /analyses`: call `check_request(participant_id, atlas)` first; pass its 7-digit `participant["participant_id"]` to `predict`; return `analysis_log.log_prediction(out)` with status 201. `check_request` also returns the checkpoint's absolute path (memo 0014 open item).

## Checks

- `ruff check src scripts tests` clean
- `pytest`: 308 passed
- `python scripts/smoke_api.py --data fixtures`: every data-side endpoint answers
- CI on this PR must be green before merging
