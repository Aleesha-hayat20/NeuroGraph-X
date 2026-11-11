# Software Requirements Specification: NeuroGraph-X

**Version:** 1.1 (draft, 8 November 2026; final 15 November 2026)
**Owners:** Aleesha Hayat, Alishba Fayaz
**Scope:** FYP-I, the system demonstrated at the FYP-I final evaluation

| Version | Date | Change |
|---|---|---|
| 1.0 | October 2026 | Requirements as listed in the FYP-I final work plan (Definition of Done, Section 2; interface contracts, Section 5); no separate document |
| 1.1 | 8 November 2026 | First full SRS, written against the built system: every endpoint, error and record field as implemented on `main`, with the test that verifies each requirement |

## 1 Introduction

### 1.1 Purpose

This document states what NeuroGraph-X must do and how well, so that the jury, the
supervisor and the team can check the delivered system against it. Each requirement has an
identifier, and section 6 names the automated test or manual test case that verifies it.

### 1.2 Product scope

NeuroGraph-X is a research platform for brain connectivity analysis in autism. It takes the
public ABIDE I resting-state fMRI data, applies quality control, builds a connectivity graph
per participant for four brain atlases, and classifies each graph with a graph neural
network (GNN). Every prediction is served through a REST API with a calibrated confidence,
the model's training run, and a record that can be listed, regenerated and exported, and is
shown in a web dashboard.

The system is for research and teaching. It is **not a diagnostic or medical device**, and
its predictions must not inform any decision about a person.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| ABIDE I | Autism Brain Imaging Data Exchange I: 1,112 participants from 17 international sites (20 site labels in the phenotypic file), shared for non-commercial research |
| Atlas | A division of the brain into regions; the four used are AAL (116 regions), CC200 (200), Harvard-Oxford (111) and Dosenbach 160 (161) |
| Connectome | The matrix of correlations between the regions' signals for one participant |
| Quality control (QC) | Three gates that exclude a participant: rater ratings, head motion (mean framewise displacement above 0.5 mm) and completeness of the time series |
| Frozen evaluation set | 100 participants held out from all training, tuning and calibration, measured once per final model |
| Development pool | The other 761 included participants, in five cross-validation folds |
| Training run | One training of a model, identified by an 8-character `run_id` in the run log |
| Analysis | One prediction for one participant on one atlas, identified by a 12-character `analysis_id` |
| Calibration | Rescaling a model's probability so that it matches observed frequencies (Platt scaling, memo 0010) |
| Fixture dataset | A small synthetic dataset in the real file formats, selected with `NGX_DATA=fixtures` (memo 0014) |

### 1.4 References

FYP-I final work plan; decision memos 0001 to 0014 in `docs/decisions/`; the API's generated
OpenAPI page at `/docs`; `docs/testing/manual_tests.md`.

## 2 Overall description

### 2.1 Users

| User | Goal |
|---|---|
| Researcher | Browse the cohort, run an analysis for a participant and atlas, compare atlases, review and export past analyses |
| Reviewer (supervisor, jury) | Check that results are traceable to a model and reproducible |
| Developer | Run the system and its tests on any machine, with or without the real data |

### 2.2 Operating environment

- Backend: Python 3.11, FastAPI, PyTorch and PyTorch Geometric on the CPU; macOS, Linux or
  Windows. Training runs separately on a GPU (Kaggle) and is not part of the served system.
- Frontend: a current desktop browser; React with Vite, reaching the API through the Vite
  proxy (memo 0012).
- Data: ABIDE I Preprocessed Connectomes Project, CPAC pipeline, band-pass filtering and
  global signal regression (memo 0002), downloaded once to the demonstration machine.

### 2.3 Constraints

- **C-1** Only public data: ABIDE I, used under its non-commercial research terms.
- **C-2** Free GPU only (Kaggle or Colab) for training; serving needs no GPU.
- **C-3** Single user, single server process on one machine in FYP-I; no accounts.
- **C-4** The released model weights are shared on the ABIDE I terms (CC BY-NC-SA 3.0,
  memo 0009).

### 2.4 Assumptions

- The phenotypic table and the stored connectomes on the demonstration machine are the
  ones the integrity check accepts (section 4.3).
- The demonstration uses frozen-set participants, because the final models were trained on
  every development participant.

## 3 Functional requirements

### 3.1 Data and quality control (M1)

- **FR-1** The system shall load the ABIDE I phenotypic table of 1,112 participants and
  report each participant's site, group, sex and age.
- **FR-2** The system shall apply the three quality gates of memo 0003 and record, for every
  excluded participant, the first gate failed, every gate failed and the reasons.
  On the real data: 861 included, 251 excluded.
- **FR-3** The system shall hold out a frozen evaluation set of 100 participants,
  stratified by site and group, drawn once with a recorded seed and never redrawn (memo
  0005), and place the other included participants in five folds.
- **FR-4** No participant shall be in both the frozen set and the development folds.

### 3.2 Connectome engine (M2)

- **FR-5** The system shall compute, for each included participant and atlas, the Pearson
  correlation matrix and its Fisher z transform, and mark regions with a flat signal.
- **FR-6** The system shall store each atlas's connectomes with a manifest holding the
  parameters and the SHA-256 of the stored file, and reuse the store when the inputs have
  not changed (memo 0007).

### 3.3 Models and inference (M3)

- **FR-7** The system shall serve one registered model per atlas, chosen through the model
  registry, never by file name.
- **FR-8** The system shall refuse to load a checkpoint whose SHA-256 differs from the one
  its training run recorded (memo 0009).
- **FR-9** The system shall apply the calibration fitted for the serving run when one
  exists, and state whether the confidence is calibrated.

### 3.4 REST API (M3 service layer)

Endpoints, as implemented (memo 0013, part 3):

| ID | Method and path | Requirement |
|---|---|---|
| FR-10 | `GET /health` | Report that the server is up, its version, the data mode and whether the participant table was found |
| FR-11 | `GET /participants` | List every participant with quality status, gate, reasons and split; filter by `site` (any case), `group` and `qc_status`; counts cover the whole table |
| FR-12 | `GET /participants/{participant_id}` | Return one participant; accept `0050003` or `50003` |
| FR-13 | `GET /atlases` | List the four atlases with region count, data availability and the registered model's run |
| FR-14 | `GET /cohort/summary` | Return the counts for the overview: total, included, excluded, by first gate, by group, by site, by split |
| FR-15 | `GET /exclusions` | Return the exclusion log; filter by first gate failed |
| FR-16 | `GET /models`, `GET /models/{atlas}` | Return the registry entry with cross-validation and frozen-set metrics and calibration |
| FR-17 | `POST /analyses` | Run the registered model of the atlas for the participant, write the analysis record and return it with status 201 |
| FR-18 | `GET /analyses` | List analyses newest first; filter by participant and atlas; `limit` from 1 to 1000 |
| FR-19 | `GET /analyses/{analysis_id}` | Return one analysis record |
| FR-20 | `POST /analyses/{analysis_id}/regenerate` | Re-run the analysis with the model of its original training run, record the repeat with `reproduces_analysis_id`, and report whether prediction, confidence and calibrated flag are identical, naming any field that differs |
| FR-21 | `GET /analyses/{analysis_id}/export` | Return the stored record as a downloaded file: `analysis_<id>.json`, or `analysis_<id>.csv` with a header row of the ten fields and one row |

- **FR-22** Every analysis record shall hold exactly the ten fields of the `analysis_log`
  table in `db/schema.sql`: `analysis_id`, `timestamp`, `participant_id`, `atlas`,
  `run_id`, `prediction`, `confidence`, `calibrated`, `git_commit`,
  `reproduces_analysis_id`. The response of FR-17, the history of FR-18 and FR-19, and the
  export of FR-21 use this one shape.
- **FR-23** Error contract (memo 0013, part 4). Every error body shall be
  `{"detail": "<one plain-language sentence>"}`, with:
  404 unknown participant or analysis; 409 participant excluded by quality control, with the
  gate and reasons; 422 invalid atlas, filter, format or request body; 503 no model
  registered, checkpoint missing or changed, or data unavailable; 500 anything unexpected.
- **FR-24** `POST /analyses` shall check, in this fixed order: atlas name (422), participant
  exists (404), participant included (409), connectomes available (503), model registered
  and checkpoint present (503).

### 3.5 Analysis log and records

- **FR-25** Analysis records shall be appended to `runs/analysis_log.jsonl` only through the
  analysis-log writer, which validates every field, refuses a duplicate `analysis_id`, a
  `run_id` that is not in the run log, and a `reproduces_analysis_id` that is not already
  recorded.
- **FR-26** The SQLite database shall be rebuilt from the run log, the registry and the
  analysis log by `scripts/build_db.py`, and contain every training run and every analysis.

### 3.6 Integrity check

- **FR-27** `scripts/check_integrity.py` shall verify that: every registry entry names a
  final run of its atlas whose checkpoint is present and matches its logged SHA-256; every
  analysis was made by a registered or archived run; the folds, frozen set, out-of-fold and
  frozen-prediction files match the hashes recorded in the runs; the frozen set and folds
  partition the QC cohort; the stored connectomes match their manifests and give the
  registered models the inputs they were trained on. It shall exit with status 0 only when
  nothing fails.

### 3.7 Dashboard (M7)

Status on 8 November: Participants, Analysis, History and Models are built (FR-29, FR-30,
FR-32, and FR-31 without its regenerate and export controls). The Overview charts, the
Exclusions page, the regenerate and export controls and the FYP-II tabs (FR-28, FR-31,
FR-33, FR-34) are scheduled for Week 7; the API side of each is built.

- **FR-28** Overview: cohort totals, the three quality gates and their counts, with charts.
- **FR-29** Participants: a table filterable by site and group, with quality badges; for an
  excluded participant the reason is shown and Run is disabled.
- **FR-30** Analysis: choose an atlas with a registered model, run, and see prediction,
  calibrated confidence, the calibrated flag, atlas, run ID and analysis ID, with the
  research-use notice; a note when the participant is in the development pool.
- **FR-31** History: every analysis, newest first, filterable by atlas and participant; one
  record in detail; regenerate with an "identical" indicator; export as JSON or CSV.
- **FR-32** Models: the four atlases with cross-validation and frozen-set metrics,
  calibration error before and after, and a reliability diagram.
- **FR-33** Exclusions: all excluded participants with gate and reason.
- **FR-34** Explanation and Reliability views are present and marked "FYP-II".
- **FR-35** Every page shows the research-use notice, and the dashboard shows when it is
  running on the fixture dataset.

## 4 Non-functional requirements

### 4.1 Reproducibility

- **NFR-1** Regenerating an analysis on the same machine shall give the identical
  prediction, confidence (4 decimals) and calibrated flag.
- **NFR-2** A training run's checkpoint is never overwritten; a new model is a new run, and
  the registry keeps the previous run IDs (memo 0009).
- **NFR-3** CPU inference shall match the training-time result within 0.001 in confidence
  (memo 0009, section 4).

### 4.2 Evaluation integrity

- **NFR-4** The frozen set is measured once per final model after the 2 November tuning
  freeze; a repeat is refused unless declared, and recorded with its reason (memo 0011).
- **NFR-5** Calibration is fitted only on out-of-fold predictions of the development pool,
  never on the frozen set (memo 0010).

### 4.3 Data integrity

- **NFR-6** The run log and the analysis log are append-only JSON Lines files; records are
  never edited or deleted.
- **NFR-7** The integrity check (FR-27) passes in CI on the fixture dataset and on the real
  data before every demonstration.
- **NFR-8** Text data files are stored with LF line endings (`.gitattributes`), and hashes of
  older CRLF copies are still accepted, so a file's identity does not depend on the
  operating system.

### 4.4 Performance

- **NFR-9** On the demonstration laptop's CPU, an analysis shall complete within 5 seconds
  once its atlas's connectomes are loaded. Measured in the Week 7 performance tests.

### 4.5 Usability

- **NFR-10** Every error shown to the user is one plain-language sentence (FR-23).
- **NFR-11** Numbers on the dashboard agree with the API and the committed reports.

### 4.6 Portability and maintainability

- **NFR-12** A clean clone, following only `SETUP.md`, reaches a running dashboard.
- **NFR-13** The whole system, including the end-to-end test, runs on the fixture dataset
  with one setting and no real data (memo 0014).
- **NFR-14** Code passes `ruff`; every merge to `main` requires green CI; test coverage of
  the Python package is at least 80%.
- **NFR-15** Settings are read from `configs/`, not written into the code.

### 4.7 Privacy, safety and licensing

- **NFR-16** Only the anonymised ABIDE I data is used; the system stores no other personal
  data.
- **NFR-17** The research-use notice is shown with every prediction (FR-30, FR-35).
- **NFR-18** Released weights carry the ABIDE I licence terms (C-4).

## 5 External interfaces

- **REST API:** JSON over HTTP on `127.0.0.1:8000`; the OpenAPI description at `/docs` is
  generated from the response models in `src/neurographx/api/schemas.py`.
- **Dashboard to API:** every call goes through one client module
  (`dashboard/src/api/client.js`) under `/api`, forwarded by the Vite proxy.
- **Files:** `runs/run_log.jsonl`, `runs/model_registry.json`, `runs/analysis_log.jsonl`,
  `runs/calibration/`, `checkpoints/`, `data/` as described in
  `src/neurographx/datasource.py`.

## 6 Verification

Automated tests run in CI on every push (pytest on the fixture dataset; Vitest; Playwright).
Manual test cases (TC) are executed in rounds 1 and 2 (Weeks 7 and 8).

| Requirement | Automated verification | Manual |
|---|---|---|
| FR-1, FR-2 | `tests/test_metadata.py`, `tests/test_qc.py`, `tests/test_screening.py` | TC-01, TC-10 |
| FR-3, FR-4 | `tests/test_frozen_set.py`, `tests/test_leakage.py`; integrity check section 4 | |
| FR-5, FR-6 | `tests/test_connectivity.py`, `tests/test_engine.py`, `tests/test_fisher_storage.py`, `tests/test_verify.py` | |
| FR-7 to FR-9 | `tests/test_inference.py`, `tests/test_calibration.py` | TC-04, TC-09 |
| FR-10 to FR-15 | `tests/test_api.py`, `tests/test_api_data.py`; `scripts/smoke_api.py` in CI | TC-01, TC-02, TC-10 |
| FR-16 | `tests/test_api_models.py` | TC-09 |
| FR-17, FR-24 | `tests/test_api_analyses.py` | TC-03, TC-04, TC-05 |
| FR-18, FR-19 | `tests/test_api_history.py` | TC-06 |
| FR-20, NFR-1 | `tests/test_api_reproduce.py`; smoke test in CI | TC-07 |
| FR-21 | `tests/test_api_reproduce.py`; smoke test in CI | TC-08 |
| FR-22, FR-25, FR-26 | `tests/test_analysis_log.py`, `tests/test_schema.py` | |
| FR-23 | `tests/test_api.py`, `tests/test_api_analyses.py`, `tests/test_api_reproduce.py` | TC-03 |
| FR-27, NFR-7, NFR-8 | `tests/test_integrity.py`; integrity step in CI | before every demonstration |
| FR-28 to FR-35 | Vitest page and component tests; Playwright `dashboard/e2e/analysis_flow.e2e.js` | TC-01 to TC-10 |
| NFR-2, NFR-4, NFR-5 | `tests/test_run_logger.py`, `tests/test_tuning.py`, `tests/test_oof.py` | |
| NFR-3 | `scripts/predict_one.py`; integrity check replay | |
| NFR-9 | Week 7 performance tests | |
| NFR-12 | Week 8 clean-clone test | |
| NFR-13, NFR-14 | CI (fixture mode, lint, coverage report) | |
