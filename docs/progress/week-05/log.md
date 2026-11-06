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

## Decisions taken
- `docs/decisions/0013-analysis-log-and-api-contract.md` (revised 27 October, for acceptance)
- `docs/decisions/0014-fixture-data.md` (amended 27 October)

## Week close, Sunday 1 November
**Gate items met:**
**Gate items missed, and why:**
**React or Streamlit (W5-18):**
**Carried into next week:**
**Board screenshot:** `board.png`
