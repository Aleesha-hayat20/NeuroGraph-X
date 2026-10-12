-- NeuroGraph-X database schema (issue #20, decision 0008).
--
-- run_log and model_registry mirror, name for name, the records written by
-- src/neurographx/m3_model/run_logger.py (runs/run_log.jsonl and
-- runs/model_registry.json). JSON objects and arrays are stored as TEXT.
-- analysis_log is the planned record of analyses run through the API.

-- One row per training run.
CREATE TABLE IF NOT EXISTS run_log (
    run_id            TEXT PRIMARY KEY,
    timestamp         TEXT NOT NULL,               -- ISO 8601, UTC
    schema_version    INTEGER NOT NULL DEFAULT 1,  -- records written before versioning count as 1
    git_commit        TEXT,                        -- NULL outside git and in version 1 records
    environment       TEXT,                        -- JSON object of library versions; NULL in version 1 records
    dataset           TEXT NOT NULL,
    atlas             TEXT,                        -- NULL for non-brain datasets
    seed              INTEGER NOT NULL,
    hyperparameters   TEXT NOT NULL,               -- JSON object
    metrics           TEXT NOT NULL,               -- JSON object
    checkpoint_path   TEXT NOT NULL,
    data_config       TEXT,                        -- JSON object, optional
    split_sizes       TEXT,                        -- JSON object, optional
    reload_identical  INTEGER CHECK (reload_identical IN (0, 1)), -- optional
    stage             TEXT CHECK (stage IN ('cv', 'final')),     -- ABIDE runs: cross-validation or the final model; NULL otherwise
    repeat_frozen_measurement INTEGER CHECK (repeat_frozen_measurement IN (0, 1))  -- final runs: 1 if the frozen set had already been measured for this atlas
);

-- One row per atlas: the model currently served for that atlas (decision 0004).
CREATE TABLE IF NOT EXISTS model_registry (
    atlas             TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL REFERENCES run_log(run_id),
    checkpoint_path   TEXT NOT NULL,
    metrics           TEXT NOT NULL,               -- JSON object, copied from the run
    registered_at     TEXT NOT NULL,               -- ISO 8601, UTC
    previous_run_ids  TEXT NOT NULL DEFAULT '[]'   -- JSON array of earlier run_ids for this atlas
);

-- One row per analysis run through the API. run_id is the training run that
-- produced the model used.
CREATE TABLE IF NOT EXISTS analysis_log (
    analysis_id             TEXT PRIMARY KEY,
    timestamp               TEXT NOT NULL,         -- ISO 8601, UTC
    participant_id          TEXT NOT NULL,
    atlas                   TEXT NOT NULL,
    run_id                  TEXT NOT NULL REFERENCES run_log(run_id),
    prediction              TEXT NOT NULL CHECK (prediction IN ('autism', 'control')),
    confidence              REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    calibrated              INTEGER NOT NULL CHECK (calibrated IN (0, 1)),
    git_commit              TEXT,
    reproduces_analysis_id  TEXT REFERENCES analysis_log(analysis_id)
);

CREATE INDEX IF NOT EXISTS idx_run_log_atlas            ON run_log(atlas);
CREATE INDEX IF NOT EXISTS idx_analysis_log_participant ON analysis_log(participant_id);
CREATE INDEX IF NOT EXISTS idx_analysis_log_run         ON analysis_log(run_id);
