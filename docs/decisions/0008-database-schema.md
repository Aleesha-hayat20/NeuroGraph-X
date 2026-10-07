# 0008. Database schema for the run log and model registry

**Status:** Proposed
**Date:** 2026-10-08
**Owner:** Alishba Fayaz
**Related:** 0004 (one model per atlas), 0005 (frozen evaluation set), 0006 (model architecture)

## Context

The run logger (`src/neurographx/m3_model/run_logger.py`) writes one JSON line per
training run to `runs/run_log.jsonl` and keeps the current model for each atlas in
`runs/model_registry.json`. The midterm asks for a database schema, and the dashboard
will later need to query runs and analyses. The schema must not drift from what the
logger actually writes.

## Decision

- The JSON files stay the source of truth. They are plain text, diff cleanly and need
  no server.
- `db/schema.sql` defines the same data as three SQLite tables. Column names equal the
  logger's field names, with no renames.
- `scripts/build_db.py` rebuilds a SQLite database from the JSON files on demand. The
  database is a disposable view and is not committed.
- `tests/test_schema.py` runs in CI and fails if the logger and the schema disagree.

| Table | One row per | Key | Source |
|---|---|---|---|
| `run_log` | training run | `run_id` | `runs/run_log.jsonl` |
| `model_registry` | atlas | `atlas`, with `run_id` referencing `run_log` | `runs/model_registry.json` |
| `analysis_log` | analysis run through the API | `analysis_id`, with `run_id` referencing `run_log` | not written yet |

JSON objects and arrays (`environment`, `hyperparameters`, `metrics`, `data_config`,
`split_sizes`, `previous_run_ids`) are stored as JSON text.

## Rationale

- **Same names as the logger.** One vocabulary across the code, the files and the schema.
- **Nullable where the logger allows it.** `atlas` is null for non-brain datasets,
  `git_commit` is null outside git, and records written before `schema_version` existed
  have no `environment`. Those records are stored with `schema_version` 1.
- **Unknown fields fail the import.** A new logger field needs a new column and a
  `schema_version` bump, so the schema cannot fall behind silently.
- **A separate `analysis_log`.** `run_id` identifies a training run and is shared by
  every prediction that model makes. Run history and regenerating a past result need an
  identifier for each analysis, which is `analysis_id`.

## Consequences

- `model_registry` repeats `checkpoint_path` and `metrics` from `run_log`, and keeps
  `previous_run_ids` as a list. This mirrors the registry file and is not normalised.
- `analysis_log` is a design until the API writes analyses. Its columns follow the
  prediction response of `m3_model/inference.py`, so `prediction` is `autism` or `control`.
- The exclusion log is not part of this schema. It is owned by the ingestion module.

## To confirm

- [ ] Laiba confirms the column list against the run logger.
- [ ] Prediction response carries `analysis_id` alongside `run_id`.
- [ ] `runs/neurographx.sqlite` is ignored by git.
