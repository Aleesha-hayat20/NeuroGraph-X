# NeuroGraph-X API reference

The REST API behind the dashboard (FastAPI, version 0.1.0). It serves the participant table
and quality control, the four atlas models, and every analysis with its record. Decisions:
memo 0013 (analysis log and API contract), 0009 (checkpoints), 0010 (calibration), 0014
(fixture data). The interactive version of this page, generated from the code, is at
`/docs` while the server runs; this file adds the error contract and examples.

**Research use only.** A prediction is a model output for research, not a diagnosis.

## Running it

```bash
make api            # real ABIDE data:  python -m uvicorn neurographx.api.main:app --reload
make api-fixtures   # synthetic fixture dataset (NGX_DATA=fixtures), no real data needed
```

Without `make` (for example in Git Bash on Windows), run the commands directly:
`python -m uvicorn neurographx.api.main:app` for real data, and
`NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app` for the fixture dataset.

Base URL: `http://127.0.0.1:8000`. Every response is JSON except the export endpoint, which
returns a file. `GET /health` reports the data mode (`real` or `fixtures`).

Real mode needs, besides the repository: the phenotypic table
(`python scripts/01_fetch_phenotypic.py`) and the connectomes in
`data/processed/connectomes/cpac_filt_global/` (built by `scripts/07_build_connectomes.py`).
The four model checkpoints are committed (`checkpoints/`).

## Error contract

Every error body is `{"detail": "<one plain-language sentence>"}`, so the dashboard can show
it as it is. A request that fails writes nothing to the analysis log. Tested by
`tests/test_robustness.py`.

| Status | When | Example `detail` |
|---|---|---|
| 404 | Unknown participant, analysis or endpoint | `Unknown participant: 0099999` |
| 405 | Method not allowed on that path | `Method DELETE is not allowed for /analyses/132ae8374154.` |
| 409 | Participant excluded by quality control | `Participant 0050002 was excluded by quality control (rater): qc_rater_1 = fail; …` |
| 422 | Unknown atlas, site or format; invalid filter, body or JSON | `Unknown atlas 'xyz'. Use one of: aal, cc200, ho, dosenbach160` |
| 503 | Data, model or checkpoint not available, or a checkpoint that does not match its recorded SHA-256 | `No model is registered for atlas 'ho'.` |
| 500 | Anything unexpected (details go to the server log, not the response) | `Internal error; see the server log.` |

Participant IDs are accepted as `0050003` or `50003` and always returned with 7 digits.
Atlas names are `aal`, `cc200`, `ho` and `dosenbach160`.

## Endpoints

| Method and path | Purpose | Success |
|---|---|---|
| `GET /health` | Server status and data mode | 200 |
| `GET /participants` | Participants with quality status; filters | 200 |
| `GET /participants/{participant_id}` | One participant | 200 |
| `GET /atlases` | The four atlases: regions, data, registered model | 200 |
| `GET /cohort/summary` | Counts for the Overview page | 200 |
| `GET /exclusions` | The exclusion log; filter by gate | 200 |
| `GET /models` | The registered model of every atlas | 200 |
| `GET /models/ensemble` | The four-atlas ensemble's recorded result (memo 0017) | 200 |
| `GET /models/{atlas}` | One atlas's model | 200 |
| `POST /analyses` | Run one analysis and record it | 201 |
| `GET /analyses` | Analysis history, newest first; filters | 200 |
| `GET /analyses/{analysis_id}` | One analysis record | 200 |
| `POST /analyses/{analysis_id}/regenerate` | Re-run a past analysis with its original model | 201 |
| `GET /analyses/{analysis_id}/export` | One record as a JSON or CSV file | 200 |

### `GET /health`

`{"status": "ok", "version": "0.1.0", "participant_table_found": true, "data_mode": "real"}`

### `GET /participants`

Query: `site` (e.g. `NYU`), `group` (`autism`, `control`), `qc_status` (`included`,
`excluded`). Returns `total`, `included` and `excluded` for the whole table (they do not
change with the filters) and `participants`, each with `participant_id`, `file_id`, `site`,
`group`, `sex`, `age`, `qc_status`, `exclusion_gate`, `exclusion_reasons` and `split`
(`frozen` or `development` for included participants).
Errors: 422 for an unknown site or an invalid filter value.

### `GET /participants/{participant_id}`

One participant, fields as above. Errors: 404 unknown participant.

### `GET /atlases`

One entry per atlas: `atlas`, `key` (e.g. `rois_cc200`), `label`, `family`, `n_regions`
(116, 200, 111, 161), `data_available`, `model_registered`, `run_id`.

### `GET /cohort/summary`

`total`, `included`, `excluded`; `excluded_by_gate` (`rater`, `motion`, `completeness`);
`by_group` and `by_site` (included and excluded counts); `by_split` (included participants
per split). Real data: 1112 participants, 861 included, 251 excluded.

### `GET /exclusions`

Query: `gate` (`rater`, `motion`, `completeness`). Returns `total` and `exclusions`, each
with `participant_id`, `file_id`, `site`, `group`, `first_gate_failed`, `gates_failed` and
`reasons`. Errors: 422 invalid gate.

### `GET /models` and `GET /models/{atlas}`

For each atlas: the registry entry (`run_id`, `registered_at`, `previous_run_ids`,
`checkpoint_path`), whether the checkpoint is present on this machine
(`checkpoint_available`), the training settings (`hyperparameters`, `graph`), the logged
metrics (cross-validation and the single frozen-set measurement), `calibrated` and the
calibration parameters and scores (`calibration`).
Errors: 422 unknown atlas; 503 no model registered.

| Atlas | Served run | Frozen accuracy |
|---|---|---|
| aal | `57900b0d` | 0.65 |
| cc200 | `cf60f29e` | 0.55 |
| ho | `76533df4` | 0.63 |
| dosenbach160 | `5ee28510` | 0.62 |

### `GET /models/ensemble`

The record that `scripts/ensemble.py --measure-once` wrote to `runs/ensemble_log.jsonl` for
the active dataset (memo 0017, section 5): `ensemble_id`, `timestamp`, `members` (atlas to
run id of the four final models), `rule` (equal-weight mean of the raw probabilities,
threshold 0.5) and `metrics`, with `cv` (out-of-fold, mean and standard deviation over the
five folds) and `frozen` (the single frozen-set measurement). Read-only: it makes no
prediction. It is a separate endpoint, not a fifth entry in `GET /models`, because that list
is one entry per atlas model with a checkpoint and a calibration.
Errors: 404 "The ensemble has not been measured on this dataset." (always the case in
fixture mode).

| Ensemble | Members | Frozen accuracy (95% CI) | Frozen AUC |
|---|---|---|---|
| `a7f3095e` | `57900b0d`, `cf60f29e`, `76533df4`, `5ee28510` | 0.62 (0.52–0.71) | 0.680 |

### `POST /analyses`

Body: `{"participant_id": "0050011", "atlas": "cc200"}`. The checks run in this fixed order,
so the same bad request always gets the same answer: atlas known (422), participant exists
(404), participant included (409), connectomes available for the atlas (503), model
registered and checkpoint present and matching its SHA-256 (503). The graph is built with
the settings of the model's training run; the prediction is made on the CPU and calibrated
with the run's Platt calibrator. Returns 201 and the stored record:

```json
{
  "analysis_id": "132ae8374154",
  "timestamp": "2026-11-20T10:15:02+00:00",
  "participant_id": "0050011",
  "atlas": "cc200",
  "run_id": "cf60f29e",
  "prediction": "control",
  "confidence": 0.5124,
  "calibrated": true,
  "git_commit": "04f01b9",
  "reproduces_analysis_id": null
}
```

`confidence` is the calibrated probability of the predicted class (0.5 to 1).

### `GET /analyses`

Query: `participant_id`, `atlas`, `limit` (1 to 1000, default 50). Returns `total` (before
the limit) and `analyses`, newest first. Errors: 422 invalid participant ID, atlas or limit.

### `GET /analyses/{analysis_id}`

One stored record. Errors: 404 unknown analysis.

### `POST /analyses/{analysis_id}/regenerate`

Runs the same participant through the model of the original analysis's training run (not
whichever model is registered today), with that run's graph settings and calibration, and
records the result with `reproduces_analysis_id` set. Returns 201 with `analysis` (the new
record), `original`, `identical` (prediction, confidence and calibrated all equal) and
`differences` (the fields that differ). Errors: 404 unknown analysis; 503 when the run, its
checkpoint or the participant's connectome is unavailable, or the checkpoint does not match
its SHA-256.

### `GET /analyses/{analysis_id}/export`

Query: `format` (`json`, default, or `csv`). Returns the stored record unchanged as a file,
`analysis_<id>.json` or `analysis_<id>.csv`. The CSV has the header
`analysis_id,timestamp,participant_id,atlas,run_id,prediction,confidence,calibrated,git_commit,reproduces_analysis_id`
and one data row. Errors: 404 unknown analysis; 422 unknown format.

## Performance

On the CPU, an analysis completes well within the 5-second requirement (NFR-9) once its
atlas's connectomes are loaded; the first request for an atlas also loads them. Measured by
`python scripts/benchmark_api.py`, which writes `docs/reports/performance.md`, and checked
by `tests/test_performance.py`. On a Windows laptop (20 November 2026), repeated analyses
took a median of 136 to 143 ms per atlas. The very first request after the server starts
took 4.55 s, because it also imports the libraries and reads the participant table, so run
one analysis before a demonstration to warm the server.

## What the API does not serve

- **A combined prediction for one participant.** Every analysis is made by one atlas's
  model; `GET /models/ensemble` reports the ensemble's recorded result only. Combined
  predictions and calibrating the ensemble are left for FYP-II (memo 0017, section 5).
- **Explanation and reliability** (dashboard tabs marked FYP-II) have no endpoints in FYP-I
  (memo 0015, memo 0016).

`tests/test_api_docs.py` checks that the endpoint table above lists exactly the endpoints the
code serves, so this page cannot fall behind the code unnoticed.
