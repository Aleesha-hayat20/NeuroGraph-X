# 0013. Analysis log storage and the API contract

**Status:** Proposed, revised 2026-10-27 (see Revisions at the end). For acceptance at the
Week 5 Thursday stand-up (29 October 2026).
Once accepted, the contract below is **frozen**: any change is an amendment to this memo,
agreed by both the API side (Aleesha, Laiba) and the dashboard side (Alishba).
**Date:** 2026-10-24
**Owner:** Aleesha Hayat
**Related:** 0003 (QC), 0004 (one model per atlas), 0005 (frozen set), 0008 (database
schema), 0009 (serving checkpoints), 0010 (calibration), 0012 (dashboard), 0014 (fixtures)

## Context

Up to now the API only lists participants. From Week 5 it runs analyses: a user picks a
participant and an atlas, the registered model makes a prediction, and the result must be
kept so it can be listed in History, regenerated, and exported. Memo 0008 already designed
the `analysis_log` table but left open where analyses are actually written and what
identifier the response carries. Two people build the two sides of the API (Laiba the model
side, Aleesha the data side) and a third builds the dashboard against it, so the shapes and
errors must be written down once and then held still.

Plain-language terms used below:

- **Training run** (`run_id`, 8 hex characters): one training of a model, logged in
  `runs/run_log.jsonl`. Every prediction a model makes shares its `run_id`.
- **Analysis** (`analysis_id`): one prediction for one participant on one atlas, requested
  through the API. Each analysis gets its own identifier.
- **Append-only:** records are only ever added at the end of the file, never changed or
  deleted, so the file is a complete history.

## Decision, part 1: where analyses are stored

1. **Source of truth: `runs/analysis_log.jsonl`**, one JSON object per line, append-only,
   the same pattern as the run log (memo 0008). In fixture mode the same relative path under
   `fixtures/` is used, and that file is ignored by git (memo 0014). The path comes from
   `datasource.analysis_log()`.
2. **SQLite is a rebuilt view.** `scripts/build_db.py` also loads the analysis log into the
   existing `analysis_log` table, whose columns already match the record below
   (`python scripts/build_db.py`, or `--data fixtures`). A test checks the two agree.
3. **One writer module** (Aleesha, Week 5): `src/neurographx/analysis_log.py` with
   `new_analysis_id()`, `make_record(prediction)`, `write_analysis(record, path)`,
   `log_prediction(prediction)` (make and write in one call),
   `read_analyses(path, participant_id=None, atlas=None)` and `get_analysis(id)`. The writer:
   - checks every field and type before writing, and refuses unknown fields;
   - refuses a duplicate `analysis_id`, a `run_id` that is not in the run log of the same
     dataset, and a `reproduces_analysis_id` that is not already in the analysis log;
   - serialises the whole line first, then appends it in one write, so a failure never
     leaves half a record;
   - holds a lock around the append, because FastAPI runs ordinary endpoint functions in a
     thread pool and two requests could otherwise write at once. One server process only
     (the default for uvicorn) in FYP-I.
4. **Only the demo machine writes to the real log.** Development uses fixture mode. The real
   `runs/analysis_log.jsonl` is committed with the demo analyses at release time, so the
   rebuilt database contains every demo analysis (work plan Section 2.2).
5. **Merging:** add `runs/*.jsonl merge=union` to `.gitattributes`. Git's built-in `union`
   merge keeps the added lines from both branches instead of reporting a conflict, which is
   right for append-only files. Because it does not check the result, the integrity check
   (Week 6) verifies that identifiers are unique after every merge.

## Decision, part 2: the analysis record

Exactly the columns of `analysis_log` in `db/schema.sql`, with the same names:

| Field | Type | Meaning |
|---|---|---|
| `analysis_id` | string, 12 lowercase hex characters | this analysis; longer than a `run_id` so the two cannot be confused |
| `timestamp` | string, ISO 8601, UTC, seconds | when the analysis was run |
| `participant_id` | string, 7 digits | zero-padded ABIDE SUB_ID, for example `"0050003"` |
| `atlas` | `"aal"`, `"cc200"`, `"ho"` or `"dosenbach160"` | the registry's atlas names |
| `run_id` | string, 8 hex characters | the training run whose model made the prediction |
| `prediction` | `"autism"` or `"control"` | |
| `confidence` | number from 0.5 to 1, 4 decimals | probability of the predicted class |
| `calibrated` | true or false | whether `confidence` has been calibrated (memo 0010) |
| `git_commit` | string or null | the code version that served the analysis |
| `reproduces_analysis_id` | string or null | set only by regenerate: the analysis this one repeats |

Example (illustrative values on a fixture participant, not a result):

```json
{"analysis_id": "3f9c2a7b10de", "timestamp": "2026-11-09T10:15:02+00:00",
 "participant_id": "0090001", "atlas": "cc200", "run_id": "1a2b3c4d",
 "prediction": "control", "confidence": 0.7121, "calibrated": false,
 "git_commit": "c419421", "reproduces_analysis_id": null}
```

The response to a new analysis **is** this record. History, the result card and export all
use the same shape, so the dashboard has one type for all three. This closes memo 0008's
open item "prediction response carries `analysis_id` alongside `run_id`".

## Decision, part 3: endpoints (work plan Section 5.1)

All paths are relative to the API root. Participant identifiers are accepted as
`"0050003"` or `"50003"`; responses always use the 7-digit form.

| Method and path | Request | Success response | Owner, week |
|---|---|---|---|
| `GET /health` | | `{status, version, participant_table_found, data_mode}` | done |
| `GET /participants` | filters: `site` (any case; an unknown site is 422 and the detail lists the sites), `group` (`autism`/`control`), `qc_status` (`included`/`excluded`); filters combine | `{total, included, excluded, participants: [Participant]}`; counts cover the whole table, the list is filtered | Aleesha, 5 |
| `GET /participants/{participant_id}` | | `Participant` | done; `split` added in 5 |
| `GET /atlases` | | `[{atlas, key, label, family, n_regions, data_available, model_registered, run_id}]`, all four | Aleesha, 5 |
| `GET /cohort/summary` | | `{total, included, excluded, excluded_by_gate: {rater, motion, completeness}, by_group: {autism: {included, excluded}, control: {...}}, by_site: [{site, included, excluded}], by_split: {frozen, development}}` | Aleesha, 5 |
| `GET /exclusions` | optional `gate`: keeps participants whose **first** failed gate it is, so the count equals `excluded_by_gate` | `{total, exclusions: [{participant_id, file_id, site, group, first_gate_failed, gates_failed: [gate], reasons: [text]}]}` from the exclusion log | Aleesha, 5 |
| `GET /models`, `GET /models/{atlas}` | | registry entries with metrics and calibration | Laiba, 5 |
| `POST /analyses` | `{"participant_id": "...", "atlas": "..."}` | **201** and the analysis record | Laiba, 5 (writes through Aleesha's writer) |
| `GET /analyses` | filters: `participant_id` (either id form), `atlas`; `limit` (default 50, 1 to 1000) | `{total, analyses: [record]}`, newest first; `total` counts every match before the limit; no analyses yet is an empty list, not an error | Aleesha, 5 |
| `GET /analyses/{analysis_id}` | | the record | Aleesha, 5 |
| `POST /analyses/{analysis_id}/regenerate` | | **201** and `{analysis: record, original: record, identical: bool, differences: [field]}` | Aleesha, 6 |
| `GET /analyses/{analysis_id}/export` | `format=json` (default) or `csv` | the record as a downloaded file, `analysis_<id>.json` or `.csv` (a header row of the 10 fields, then one row) | Aleesha, 6 |

**`Participant`** keeps today's fields (`participant_id`, `file_id`, `site`, `group`, `sex`,
`age`, `qc_status`, `exclusion_reasons`) and gains:

- `exclusion_gate`: `"rater"`, `"motion"`, `"completeness"` or null;
- `split`: `"frozen"`, `"development"` or null (excluded). The dashboard shows a note when
  a participant is in the development pool: the final models were trained on all 761
  development participants, so a prediction for one of them is not an independent test.
  Demonstrations use frozen-set participants.

**Where quality status comes from.** From Week 5, `qc_status`, `exclusion_gate` and
`exclusion_reasons` are read from the committed outputs of `scripts/05_apply_qc.py`
(`data/splits/qc_cohort.csv` and `docs/reports/exclusion_log.csv`) instead of re-screening
the phenotypic table on every request. The phenotypic table still supplies site, sex and
age. Reasons: the committed files include the completeness gate, which the live screen
cannot apply without the downloaded time series; they are exactly the cohort the models
were trained and evaluated on; and the dashboard's counts then always match the report. A
participant who is in the phenotypic table but in neither file is a data error (503), and
the integrity check flags it. The reason strings change to the exclusion log's wording
(for example `qc_rater_1 = fail`); `tests/test_api.py` is updated with the change.

**Regenerate** re-runs the original participant and atlas **with the original `run_id`'s
checkpoint**, not whichever model is registered now, because the point is to show the
earlier result can be reproduced. If calibration parameters exist for that run they are
applied exactly as before. `identical` is true when `prediction`, `confidence` (to 4
decimals) and `calibrated` all match; `differences` names any field that does not. The
new record's `reproduces_analysis_id` is the original's `analysis_id`. If the original
run's checkpoint is no longer available, the answer is 503 with that reason.

## Decision, part 4: the error contract

Every error body is `{"detail": "<one plain-language sentence>"}`. FastAPI's own
request-validation errors return a list under `detail` by default; a handler for
`RequestValidationError` turns that list into one sentence so the dashboard can always
show `detail` as text.

| Status | When | Example `detail` |
|---|---|---|
| 404 | unknown participant or analysis | "Unknown participant: 0059999" |
| 409 | participant excluded by quality control | "Participant 0050002 was excluded by quality control (rater): qc_rater_1 = fail" |
| 422 | invalid atlas name, filter value or request body | "Unknown atlas 'cc400'. Use one of: aal, cc200, ho, dosenbach160" |
| 503 | no model registered for the atlas, its checkpoint missing, or the data not available | "No model is registered for atlas 'ho'" |
| 500 | anything unexpected; logged with the request | "Internal error; see the server log" |

The order of checks for `POST /analyses` is fixed, so the same request always gets the
same error: atlas name (422), participant exists (404), participant included (409),
connectomes available for the atlas (503), model registered and checkpoint present (503).

## Decision, part 5: how the dashboard reaches the API (no CORS rule)

The dashboard's development server (Vite, `http://localhost:5173`) and the API
(`http://127.0.0.1:8000`) are different origins: a browser normally blocks a page from
calling a server at a different address unless that server sends permission headers
(CORS, cross-origin resource sharing). Memo 0012 (accepted 26 October) solves this on the
dashboard side instead: Vite's development proxy forwards every request under `/api` to
`http://127.0.0.1:8000` and removes the prefix, and `vite preview` uses the same proxy.
To the browser, the dashboard and the API then share one origin.

So the API adds **no** CORS middleware, its routes stay exactly as listed in part 3, and
memo 0012 records "a CORS rule in the API" as a rejected alternative. If the dashboard is
ever served from somewhere the proxy does not cover (for example the FYP-II Docker
package), the rule is decided then, as an amendment to this memo.

## Rationale

- **JSON Lines as the source, SQLite as a view** is the pattern the run log already uses
  (memo 0008): readable without tools, diffable, and nothing to keep in sync by hand.
- **The record equals the table row** so that the writer, the database, the API response
  and the export cannot drift apart; `tests/test_analysis_log.py` checks the writer's fields
  against the table's columns.
- **A longer `analysis_id`** costs nothing and prevents a run and an analysis from being
  mistaken for each other in the dashboard or the report.
- **Status from the committed QC outputs** gives one answer to "who is in the cohort"
  everywhere in the system, including the completeness gate.
- **Regenerate with the original model** makes "the result is identical" a meaningful claim:
  same participant, same data, same checkpoint, same answer.
- **A fixed order of error checks** makes the error contract testable on fixture data
  (memo 0014 plants a participant for each case).

## Consequences

- New module `src/neurographx/analysis_log.py` and its tests
  (`tests/test_analysis_log.py`); `scripts/build_db.py` and `src/neurographx/utils/db.py`
  extended to the analysis log (Aleesha, Week 5).
- `tests/test_api.py` changes where reason strings change. The test that the live screen
  agrees with the QC script moves to `tests/test_screening.py`, and the API is tested
  against the committed QC outputs (on fixture data in CI; on real data in the integrity
  check).
- Laiba's `POST /analyses` makes three calls and writes nothing itself:
  `api.analysis_checks.check_request(participant_id, atlas)` (checks 1 to 5 of part 4, in
  order, raising the documented errors), then `inference.predict(...)` with the 7-digit
  participant id, then `analysis_log.log_prediction(prediction)`, whose return value is the
  response body.
- From the Week 5 Thursday stand-up the contract is frozen. A change needs an amendment
  here and a matching change on both sides in the same pull request.

## To confirm

- [ ] Laiba: `POST /analyses` and the model endpoints follow parts 3 and 4.
- [ ] Alishba: the single API client module (memo 0012) uses these shapes through the Vite
  proxy.
- [ ] Aleesha: writer, history, and data-side endpoints with tests on fixture data.
- [ ] `.gitattributes` with `runs/*.jsonl merge=union` committed.
- [ ] Accepted at the Week 5 Thursday stand-up.

## Revisions

### 2026-10-27, before acceptance

- **Part 5 replaced.** It proposed a CORS rule in the API. Memo 0012, accepted on
  26 October, routes the dashboard's calls through Vite's proxy and lists a CORS rule as a
  rejected alternative, so the two memos contradicted each other. Part 5 now adopts the
  proxy, and the API has no CORS middleware.
- **Shapes made exact while building them (part 3):** the fields of `GET /cohort/summary`
  (adds `by_split`); `GET /exclusions` returns `{total, exclusions}` like the other lists
  rather than a bare list, and its `gate` filter is on the first failed gate; `site`
  matching ignores case and an unknown site is a 422; `limit` on `GET /analyses` runs from
  1 to 1000.
- **Consequences:** the three calls `POST /analyses` makes are named.
