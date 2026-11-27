# Manual test round 2

**Date:** Monday 23 November 2026. **Build:** `08264c4` (`main`). **Data:** real ABIDE data, API in real mode
(`/health`: `"data_mode": "real"`); fixture mode only for TC-05 step 4.
Dashboard run with Node.js 26.13.1 (CI uses Node 24).
**Definitions:** `manual_tests.md`. **Cross-testing:** Laiba Afridi ran the dashboard cases on the pages built by
Alishba, on the build with the round 1 fixes (#198, #199, #200, PR #203). The API checks of this round (#182) were run by Alishba Fayaz on build `678e8d7` (`main`, 24 November 2026).

## Summary

| Result | API checks | Dashboard cases |
|---|---|---|
| Pass | 14 (AC-01 to AC-14) | 11 (TC-01 to TC-10, TC-04b) |
| Fail | 0 | 0 |
| Blocked | 0 | 0 |
| Not run | 0 | 0 |

Bugs filed: none. The three round 1 bugs are fixed: #198 (TC-04b), #199 (TC-05) and #200 (TC-09) now pass.

**Data flow.** The dashboard cases created five analyses: TC-04 (`f860a0a32b01`), TC-04b
(`d9fa4dcafe9c`), TC-05 (`8e961098688e`, and a second Harvard-Oxford record because Run analysis
was pressed twice) and TC-07 (`735a652dbc79`, regenerating `f860a0a32b01`). `scripts/build_db.py`
then imported the run log and the analysis log into SQLite with every record present: 64 runs,
4 registered models and 5 analyses (real data). The test analyses were then removed from
`runs/analysis_log.jsonl`, which holds only demonstration analyses (memo 0013).

The API checks created five analyses: AC-06 (`e0b1b82b712d`), AC-07 (`ccdb659092d1`,
`96601ae45249`, `7e682524b16c`) and AC-09 (`a656b46ecbeb`, regenerating `e0b1b82b712d`).
`scripts/build_db.py` then imported 64 runs, 4 registered models and 12 analyses (real
data): the seven demonstration analyses already in the log and these five. The test
analyses were then removed from `runs/analysis_log.jsonl`.

## API checks

Tester Alishba Fayaz, 24 November 2026, build `678e8d7`. The API ran on Windows with
Python 3.14, PyTorch 2.11.0 (CPU) and PyTorch Geometric 2.8.0.post1; PyYAML was 6.0.3
instead of the pinned 6.0.2, which has no Python 3.14 build for Windows.

| ID | Backs | Actual result | Status |
|---|---|---|---|
| AC-01 | all | 200; `"status":"ok"`, `"version":"0.1.0"`, `"participant_table_found":true`, `"data_mode":"real"` | Pass |
| AC-02 | TC-01 | Total 1112, included 861, excluded 251; by gate rater 241, motion 10, completeness 0; by split frozen 100, development 761; by group autism 396 and 143, control 465 and 108; 20 sites | Pass |
| AC-03 | TC-02 | 184, 172 and 74 participants; totals 1112, 861 and 251 in every response | Pass |
| AC-04 | TC-03 | 0050002: PITT, autism, excluded at the rater gate with the reasons `qc_rater_1 = fail`, `qc_func_rater_2 = fail`, `qc_func_rater_3 = fail`; the POST returned 409 `Participant 0050002 was excluded by quality control (rater): qc_rater_1 = fail; qc_func_rater_2 = fail; qc_func_rater_3 = fail`, and the analysis log stayed at 7 lines | Pass |
| AC-05 | TC-04 | aal 116, cc200 200, ho 111, dosenbach160 161 regions; data present and a model registered for each (runs `57900b0d`, `cf60f29e`, `76533df4`, `5ee28510`) | Pass |
| AC-06 | TC-04 | 201; analysis `e0b1b82b712d`, run `cf60f29e`, `control`, 0.5124, calibrated, `git_commit` `678e8d7`, `reproduces_analysis_id` null | Pass |
| AC-07 | TC-05 | ho `76533df4` autism 0.6174; aal `57900b0d` autism 0.777; dosenbach160 `5ee28510` autism 0.6709; each 201, calibrated, with a 12-character ID | Pass |
| AC-08 | TC-06 | 6 analyses for 0050011, newest first: the four from AC-06 and AC-07 (dosenbach160, aal, ho, cc200), then two earlier CC200 demonstration analyses (`1c270485a07c`, `e9b14e874db6`); with the atlas filter, CC200 analyses only; the single record has the ten fields of memo 0013 | Pass |
| AC-09 | TC-07 | 201; identical true, no differing field; the new record `a656b46ecbeb` reproduces `e0b1b82b712d` with run `cf60f29e`, `control`, 0.5124, calibrated | Pass |
| AC-10 | TC-08 | 200 each; `analysis_e0b1b82b712d.json` and `analysis_e0b1b82b712d.csv`; the JSON has the ten fields; the CSV has the ten-field header and one data row | Pass |
| AC-11 | TC-09 | Four atlases, each calibrated (Platt); frozen accuracy, balanced accuracy and AUC aal 0.65, 0.6518, 0.6659; cc200 0.55, 0.5479, 0.6248; ho 0.63, 0.6236, 0.6816; dosenbach160 0.62, 0.6176, 0.6679, equal to the model cards at three decimals | Pass |
| AC-12 | TC-10 | 251, then 10 at the motion gate; 0050039 PITT, control, `func_mean_fd = 0.602 > 0.5` | Pass |
| AC-13 | TC-04, TC-05 | 422 `Unknown atlas 'xyz'. Use one of: aal, cc200, ho, dosenbach160`; 404 `Unknown participant: 0099999` | Pass |
| AC-14 | data flow | `64 runs, 4 registered models, 12 analyses (real data)`; the run log has 64 lines and the analysis log 12 | Pass |

## Dashboard cases

### TC-01 Cohort overview

| Field | |
|---|---|
| **Use case** | Supporting view: cohort overview (no use case in the diagram) |
| **Steps** | 1. Open the Overview page. 2. Read the totals. 3. Read the quality-gate counts. 4. Look at the charts. |
| **Expected result** | 1,112 participants: 861 included, 251 excluded by quality control. Excluded by first gate: rater 241, motion 10, completeness 0. Included by split: 100 frozen, 761 development. The charts by group (autism 396 included and 143 excluded, control 465 and 108) and by site (20 sites) agree with these totals. Same numbers as `GET /cohort/summary`. |
| **Actual result** | As expected. Overview: 1,112 participants, 861 included, 251 excluded by quality control; excluded by first gate rater 241, motion 10, completeness 0; included by split frozen 100, development 761; by group autism 396 included and 143 excluded, control 465 and 108; 20 site bars, whose included and excluded counts sum to 861 and 251. Footer: API ok, data real. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-02 Browse and filter participants

| Field | |
|---|---|
| **Use case** | Select participant (supporting view: browse and filter) |
| **Steps** | 1. Open Participants. 2. Filter site = NYU. 3. Add quality status = included. 4. Add group = autism. 5. Clear all filters. |
| **Expected result** | Step 2: 184 NYU participants. Step 3: 172. Step 4: 74. Step 5: all 1,112 again. The header totals (1,112 / 861 / 251) do not change while filtering. Each row shows a quality badge. |
| **Actual result** | As expected. Participants showed 1,112; Site NYU 184; with Quality included 172; with Group autism 74; filters cleared, 1,112 again. The header totals stayed 1,112, 861 and 251 while filtering, and every row had a quality badge. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-03 Excluded participant cannot be analysed

| Field | |
|---|---|
| **Use case** | Select participant (an excluded participant) |
| **Steps** | 1. Open Participants. 2. Find participant 0050002 (PITT) in the table. |
| **Expected result** | Quality badge "excluded", with the reasons "qc_rater_1 = fail", "qc_func_rater_2 = fail", "qc_func_rater_3 = fail". The Run button is disabled and its reason is shown. No analysis is created: History shows no new record (check this once the History page is merged). |
| **Actual result** | As expected. 0050002 (PITT): quality badge excluded, with the reasons `qc_rater_1 = fail`, `qc_func_rater_2 = fail` and `qc_func_rater_3 = fail`; the Run button was disabled with its reason shown. History showed no record for 0050002. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-04 Run an analysis

| Field | |
|---|---|
| **Use case** | Run analysis |
| **Steps** | 1. In Participants, press Run on participant 0050011 (frozen set). 2. On the Analysis page, check the four atlases are offered. 3. Choose CC200. 4. Run. |
| **Expected result** | Four atlases listed, each showing its number of regions and whether a model is registered. The result shows the prediction (autism or control), the confidence as a percentage from 50 to 100 under the label "Confidence in this prediction", a badge "calibrated" or "not calibrated" that matches the calibrated flag, the atlas, the model's run ID and a new 12-character analysis ID, with the research-use notice. No development-pool note appears, because 0050011 is in the frozen evaluation set. |
| **Actual result** | As expected. 0050011 (PITT, autism) with CC200: `control`, 51.2% under "Confidence in this prediction", calibrated, run `cf60f29e`, analysis `f860a0a32b01` at 2026-11-23 10:23:27 UTC. The four atlases were listed with their region counts (AAL 116, CC200 200, Harvard-Oxford 111, Dosenbach 160 161), each selectable because each has a registered model. No development-pool note was shown. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-04b Development-pool note

| Field | |
|---|---|
| **Use case** | Run analysis (development-pool participant) |
| **Steps** | 1. Pick any retained participant from `data/splits/cv5_folds.csv` (the development pool) and write the ID in the Actual result. 2. In Participants, press Run on that participant. 3. Choose CC200. 4. Run. |
| **Expected result** | The result is shown as in TC-04, with a note that the participant is in the development pool: the final models were trained on all 761 development participants, so the prediction is not an independent test (memo 0013). |
| **Actual result** | As expected. Development-pool participant 0050003 (PITT, autism; fold 4 in `cv5_folds.csv`) with CC200: `autism`, 70.5%, calibrated, run `cf60f29e`, analysis `d9fa4dcafe9c` at 2026-11-23 10:46:29 UTC. Below the result: "This participant is in the development pool: the final models were trained on all 761 development participants, so this prediction is not an independent test." Bug #198 is fixed. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-05 Same participant on a second atlas

| Field | |
|---|---|
| **Use case** | Run analysis (another atlas) |
| **Steps** | 1. Keep participant 0050011. 2. Choose a second atlas with a registered model. 3. Run. 4. Look at an atlas that has no registered model, if one exists. |
| **Expected result** | A second result with a different analysis ID and that atlas's run ID. An atlas without a registered model cannot be chosen: its option is disabled with the note "no model registered", and no analysis is created. A direct request to the API for such an atlas returns 503 "No model is registered for atlas '...'." If every atlas has a model at test time, run step 4 in fixture mode, where Harvard-Oxford has data but no model. |
| **Actual result** | As expected. Steps 1 to 3: 0050011 with Harvard-Oxford gave `autism`, 61.7%, calibrated, run `76533df4`, a new analysis `8e961098688e` (TC-04 was `f860a0a32b01`). Run analysis was pressed twice, so a second, identical Harvard-Oxford record (10:47:27) was also created. Step 4 (fixture mode; footer "data: fixtures" and the fixture-data banner shown): Harvard-Oxford (111 regions) was disabled with the note "no model registered" and could not be chosen; AAL and Dosenbach 160 were disabled with "no connectomes"; no analysis was run. Bug #199 is fixed. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-06 Analysis history

| Field | |
|---|---|
| **Use case** | View run history |
| **Steps** | 1. Open History. 2. Filter by participant 0050011. 3. Filter by atlas CC200. 4. Open one record. |
| **Expected result** | Both analyses listed, newest first. Step 3 leaves only the CC200 analysis. Step 4 shows all ten fields of the record, the same as `GET /analyses/{analysis_id}`. |
| **Actual result** | As expected. History held four analyses, newest first. For participant 0050011: three, the two Harvard-Oxford analyses from TC-05 (10:47:32, `8e961098688e`, and 10:47:27, both `autism` 61.7%; Run analysis was pressed twice), then CC200 (10:23:27, `control` 51.2%). With Atlas CC200 added: 1 of 1, the CC200 analysis only. An opened record (`d9fa4dcafe9c`) showed the ten fields of memo 0013: analysis ID, time, participant, atlas, run ID `cf60f29e`, prediction, confidence (70.5%, calibrated), calibrated yes, git commit `08264c4`, reproduces analysis none. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-07 Regenerate a past analysis

| Field | |
|---|---|
| **Use case** | Regenerate past result |
| **Steps** | 1. In History, open the CC200 analysis of 0050011. 2. Press Regenerate. |
| **Expected result** | A new record appears, pointing to the original (`reproduces_analysis_id`), with the same run ID. The dashboard shows the result is identical: same prediction, same confidence to 4 decimals, same calibrated flag. |
| **Actual result** | As expected. Regenerate on `f860a0a32b01` (0050011, CC200) showed "Identical to the original.": original `f860a0a32b01` control, 51.2% (calibrated); regenerated `735a652dbc79` control, 51.2% (calibrated). The new record (2026-11-23 10:53:53 UTC) has run `cf60f29e`, calibrated yes, git commit `08264c4`, and "Reproduces analysis" `f860a0a32b01`; History for 0050011 and CC200 then listed both records, newest first. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-08 Export an analysis record

| Field | |
|---|---|
| **Use case** | Export report |
| **Steps** | 1. Open one analysis. 2. Export as JSON. 3. Export as CSV. 4. Open both files. |
| **Expected result** | Files named `analysis_<id>.json` and `analysis_<id>.csv`. JSON holds the ten fields; CSV has one header row of the ten field names and one data row. Values match the record on screen. |
| **Actual result** | As expected. From the record `f860a0a32b01`, Export JSON and Export CSV saved `analysis_f860a0a32b01.json` and `analysis_f860a0a32b01.csv`. The JSON holds the ten fields; the CSV has the header `analysis_id,timestamp,participant_id,atlas,run_id,prediction,confidence,calibrated,git_commit,reproduces_analysis_id` and one data row (`0050011`, `cc200`, `cf60f29e`, `control`, 0.5124, `true`, `08264c4`, empty reproduces), the values shown on screen. Note: Excel displays the participant as 50011 because it drops leading zeros; the file itself holds `0050011`. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-09 Models and calibration

| Field | |
|---|---|
| **Use case** | Supporting view: models and calibration (no use case in the diagram) |
| **Steps** | 1. Open Models. 2. Check each atlas. 3. Open the reliability diagram of one atlas. |
| **Expected result** | All four atlases with cross-validation and frozen-set metrics, the majority-class baseline, calibration error before and after calibration, and a reliability diagram. Figures equal the registry (`GET /models`) and the model cards in `docs/model_cards/`. |
| **Actual result** | As expected. Models listed all four atlases with run, CV accuracy (5-fold), frozen accuracy, majority baseline (frozen), frozen AUC and ECE before and after calibration: AAL `57900b0d` 68.7% ± 1.5, 65.0%, 54.0%, 0.666, 0.250 → 0.096; CC200 `cf60f29e` 68.3% ± 2.6, 55.0%, 54.0%, 0.625, 0.398 → 0.168; Harvard-Oxford `76533df4` 67.5% ± 1.9, 63.0%, 54.0%, 0.682, 0.334 → 0.185; Dosenbach 160 `5ee28510` 65.8% ± 2.6, 62.0%, 54.0%, 0.668, 0.359 → 0.051, equal to the model cards. The majority baseline is shown (bug #200 is fixed). Reliability diagrams for each atlas (before dashed, after solid, perfect diagonal) on the out-of-fold predictions, with the out-of-fold ECE (AAL 0.170 → 0.082, CC200 0.180 → 0.091), equal to `runs/calibration/`. Balanced accuracy is not shown on this page; the case does not require it. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |

### TC-10 Exclusion log

| Field | |
|---|---|
| **Use case** | View exclusion log |
| **Steps** | 1. Open Exclusions. 2. Filter by gate = motion. 3. Find participant 0050039. |
| **Expected result** | 251 excluded participants, each with gate and reason. Step 2: 10 participants. Step 3: PITT, control, reason "func_mean_fd = 0.602 > 0.5". Same as `GET /exclusions` and `docs/reports/exclusion_log.csv`. |
| **Actual result** | As expected. Exclusions: "251 participants excluded by quality control. First gate failed: rater 241, motion 10, completeness 0." With first gate motion: showing 10 of 251, each with gate and reason; 0050039 is PITT, control, first and all gates failed motion, reason `func_mean_fd = 0.602 > 0.5`. |
| **Status** | Pass |
| **Tester** | Laiba Afridi |
| **Date** | 23 November 2026 |
| **Build** | `08264c4` |
