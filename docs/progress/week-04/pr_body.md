## What this adds (Week 4, Aleesha)

- **Fixture dataset and fixture mode (memo 0014).** `fixtures/` holds a small SYNTHETIC cohort in exactly the real file formats: phenotypic table (106 real columns), QC cohort and exclusion log, frozen set and folds, CC200 and Harvard-Oxford connectomes (`.npz` + manifest), run log, registry and a tiny registered CC200 checkpoint. Only the inputs are invented; every output file is written by the project's own QC, splits, connectome engine and run-logger code. One setting, `NGX_DATA=fixtures`, points the API at it (`src/neurographx/datasource.py`); `/health` now reports `data_mode`.
- **Memo 0011:** tuning grid (12 configurations per atlas), selection by mean CV balanced accuracy, tuning freeze 2 November, one frozen measurement per atlas after the freeze; CC200's second measurement only as a declared repeat.
- **Memo 0013:** append-only `runs/analysis_log.jsonl` with SQLite rebuilt from it; the analysis record; every FYP-I endpoint; the error contract (404, 409, 422, 503); CORS for the dashboard.
- **Clean-up:** memo 0006 note on Week 1 figures (QC cohort 861, Harvard-Oxford 198); `atlas_summary.md` marked superseded; README's "around 80 per cent" replaced with the cited figures (Heinsfeld et al. 2018: 70 per cent; Parisot et al. 2018: 70.4 per cent).

## For Alishba

Run the dashboard against `make api-fixtures` (or `NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app --reload`). `/health` returns `data_mode: "fixtures"`, useful for a banner. Please review memo 0013, which freezes the contract from the Week 5 Thursday stand-up.

## For Laiba

Please review memo 0011 before any tuning run, and memo 0013 part 3 for `POST /analyses`. Open item from memo 0014: resolve registry checkpoint paths with `datasource.checkpoint()`.

## Checks

- `ruff check src scripts tests` clean
- `pytest`: all tests pass, including 26 fixture tests and 15 data-mode tests
- `python scripts/smoke_api.py --data fixtures`: the real server answers on fixture data (new CI step)
- CI on this PR must be green before merging
