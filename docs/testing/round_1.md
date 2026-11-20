# Manual test round 1

**Date:** Friday 20 November 2026. **Build:** `04f01b9` (`feature/week7-reliability-tests`,
on top of `main` at `87e2ba5`). **Data:** real ABIDE data, API in real mode
(`/health`: `"data_mode": "real"`); fixture mode only for TC-05 step 4.
**Definitions:** `manual_tests.md`. **Cross-testing:** Aleesha Hayat ran the API checks on
the endpoints built by Laiba and Alishba and the dashboard cases on the pages built by
Alishba. AC-09 and AC-10 cover regenerate and export at the API, which Aleesha built, and
are run by Laiba Afridi.

## Summary

| Result | API checks | Dashboard cases |
|---|---|---|
| Pass | 12 (AC-01 to AC-08, AC-11 to AC-14) | 8 (TC-01 to TC-04, TC-06 to TC-08, TC-10) |
| Fail | 0 | 2 (TC-05, TC-09) |
| Blocked | 0 | 1 (TC-04b) |
| Not run | 2 (AC-09, AC-10) | 0 |

Bugs filed: #198 development-pool note (TC-04b), #199 atlas without a model can be chosen
(TC-05), #200 majority-class baseline missing on the Models page (TC-09). All three are in
the dashboard; the API answered correctly in every case.

**Data flow.** The API checks created four analyses (AC-06, AC-07) and the dashboard cases
three (TC-04, TC-05, TC-07). After each part, `scripts/build_db.py` imported the run log and
the analysis log into SQLite with every record present: 64 runs, 4 registered models and 4
analyses, then 64, 4 and 3. The test analyses were then removed from
`runs/analysis_log.jsonl`, which holds only demonstration analyses (memo 0013).

## API checks

Tester Aleesha Hayat, 20 November 2026, build `04f01b9`, unless the row says otherwise.

| ID | Backs | Actual result | Status |
|---|---|---|---|
| AC-01 | all | 200; `"status":"ok"`, `"version":"0.1.0"`, `"participant_table_found":true`, `"data_mode":"real"` | Pass |
| AC-02 | TC-01 | Total 1112, included 861, excluded 251; by gate rater 241, motion 10, completeness 0; by split frozen 100, development 761; by group autism 396 and 143, control 465 and 108; 20 sites | Pass |
| AC-03 | TC-02 | 184, 172 and 74 participants; totals 1112, 861 and 251 in every response | Pass |
| AC-04 | TC-03 | 0050002: PITT, autism, excluded at the rater gate with the three reasons; the POST returned 409 with that gate and those reasons in `detail`, and no record was added | Pass |
| AC-05 | TC-04 | aal 116, cc200 200, ho 111, dosenbach160 161 regions; data present and a model registered for each (runs `57900b0d`, `cf60f29e`, `76533df4`, `5ee28510`) | Pass |
| AC-06 | TC-04 | 201; analysis `132ae8374154`, run `cf60f29e`, `control`, 0.5124, calibrated, `git_commit` `04f01b9`, `reproduces_analysis_id` null | Pass |
| AC-07 | TC-05 | ho `76533df4` autism 0.6174; aal `57900b0d` autism 0.777; dosenbach160 `5ee28510` autism 0.6709; each calibrated, each with a 12-character ID | Pass |
| AC-08 | TC-06 | 4 analyses for 0050011, newest first (dosenbach160, aal, ho, cc200); with the atlas filter, the CC200 analysis only; the single record has the ten fields of memo 0013 | Pass |
| AC-09 | TC-07 | Not run in this round: cross-test assigned to Laiba Afridi | Not run |
| AC-10 | TC-08 | Not run in this round: cross-test assigned to Laiba Afridi | Not run |
| AC-11 | TC-09 | Four atlases, each calibrated (Platt); frozen accuracy, balanced accuracy and AUC aal 0.65, 0.6518, 0.6659; cc200 0.55, 0.5479, 0.6248; ho 0.63, 0.6236, 0.6816; dosenbach160 0.62, 0.6176, 0.6679, equal to the model cards at three decimals | Pass |
| AC-12 | TC-10 | 251, then 10 at the motion gate; 0050039 PITT, control, `func_mean_fd = 0.602 > 0.5` | Pass |
| AC-13 | TC-04, TC-05 | 422 `Unknown atlas 'xyz'. Use one of: aal, cc200, ho, dosenbach160`; 404 `Unknown participant: 0099999` | Pass |
| AC-14 | data flow | `64 runs, 4 registered models, 4 analyses (real data)`; the run log has 64 lines and the analysis log 4 | Pass |

## Dashboard cases

### TC-01 Cohort overview

| Field | |
|---|---|
| **Use case** | Supporting view: cohort overview (no use case in the diagram) |
| **Steps** | 1. Open the Overview page. 2. Read the totals. 3. Read the quality-gate counts. 4. Look at the charts. |
| **Expected result** | 1,112 participants: 861 included, 251 excluded by quality control. Excluded by first gate: rater 241, motion 10, completeness 0. Included by split: 100 frozen, 761 development. The charts by group (autism 396 included and 143 excluded, control 465 and 108) and by site (20 sites) agree with these totals. Same numbers as `GET /cohort/summary`. |
| **Actual result** | As expected. Overview: 1,112 participants, 861 included, 251 excluded by quality control; excluded by first gate rater 241, motion 10, completeness 0; included by split frozen 100, development 761; by group autism 396 included and 143 excluded, control 465 and 108; 20 site bars. Equal to AC-02. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-02 Browse and filter participants

| Field | |
|---|---|
| **Use case** | Select participant (supporting view: browse and filter) |
| **Steps** | 1. Open Participants. 2. Filter site = NYU. 3. Add quality status = included. 4. Add group = autism. 5. Clear all filters. |
| **Expected result** | Step 2: 184 NYU participants. Step 3: 172. Step 4: 74. Step 5: all 1,112 again. The header totals (1,112 / 861 / 251) do not change while filtering. Each row shows a quality badge. |
| **Actual result** | As expected. Showing 1,112 of 1,112; Site NYU 184; with Quality included 172; with Group autism 74; cleared, 1,112 again. The cohort sentence stayed 1,112, 861 and 251, and every row had a quality badge. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-03 Excluded participant cannot be analysed

| Field | |
|---|---|
| **Use case** | Select participant (an excluded participant) |
| **Steps** | 1. Open Participants. 2. Find participant 0050002 (PITT) in the table. |
| **Expected result** | Quality badge "excluded", with the reasons "qc_rater_1 = fail", "qc_func_rater_2 = fail", "qc_func_rater_3 = fail". The Run button is disabled and its reason is shown. No analysis is created: History shows no new record (check this once the History page is merged). |
| **Actual result** | As expected. 0050002 (PITT) showed the excluded badge and the reasons `qc_rater_1 = fail; qc_func_rater_2 = fail; qc_func_rater_3 = fail`; the Run button was disabled with the reason `An excluded participant cannot be analysed.`; History held no record for 0050002. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-04 Run an analysis

| Field | |
|---|---|
| **Use case** | Run analysis |
| **Steps** | 1. In Participants, press Run on participant 0050011 (frozen set). 2. On the Analysis page, check the four atlases are offered. 3. Choose CC200. 4. Run. |
| **Expected result** | Four atlases listed, each showing its number of regions and whether a model is registered. The result shows the prediction (autism or control), the confidence as a percentage from 50 to 100 under the label "Confidence in this prediction", a badge "calibrated" or "not calibrated" that matches the calibrated flag, the atlas, the model's run ID and a new 12-character analysis ID, with the research-use notice. No development-pool note appears, because 0050011 is in the frozen evaluation set. |
| **Actual result** | As expected. 0050011 with CC200: `control`, 51.2%, calibrated, run `cf60f29e`, analysis `e7842d068d2c` at 2026-11-20 10:22:08 UTC. The four atlases were listed with their region counts and a model each. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-04b Development-pool note

| Field | |
|---|---|
| **Use case** | Run analysis (development-pool participant) |
| **Steps** | 1. Pick any retained participant from `data/splits/cv5_folds.csv` (the development pool) and write the ID in the Actual result. 2. In Participants, press Run on that participant. 3. Choose CC200. 4. Run. |
| **Expected result** | The result is shown as in TC-04, with a note that the participant is in the development pool: the final models were trained on all 761 development participants, so the prediction is not an independent test (memo 0013). |
| **Actual result** | The development-pool note is not in the dashboard at this build, so the case could not be run. Bug #198. |
| **Status** | Blocked |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-05 Same participant on a second atlas

| Field | |
|---|---|
| **Use case** | Run analysis (another atlas) |
| **Steps** | 1. Keep participant 0050011. 2. Choose a second atlas with a registered model. 3. Run. 4. Look at an atlas that has no registered model, if one exists. |
| **Expected result** | A second result with a different analysis ID and that atlas's run ID. An atlas without a registered model cannot be chosen: its option is disabled with the note "no model registered", and no analysis is created. A direct request to the API for such an atlas returns 503 "No model is registered for atlas '...'." If every atlas has a model at test time, run step 4 in fixture mode, where Harvard-Oxford has data but no model. |
| **Actual result** | Steps 1 to 3 as expected: Harvard-Oxford gave `autism`, 61.7%, calibrated, run `76533df4`, a new analysis `2c29a9422d90`. Step 4 (fixture mode): Harvard-Oxford showed `no model registered` but could still be chosen, and Run analysis sent the request; the API refused it with `No model is registered for atlas 'ho'.` and no result card or record was created. Expected: the option cannot be chosen. Bug #199. |
| **Status** | Fail |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-06 Analysis history

| Field | |
|---|---|
| **Use case** | View run history |
| **Steps** | 1. Open History. 2. Filter by participant 0050011. 3. Filter by atlas CC200. 4. Open one record. |
| **Expected result** | Both analyses listed, newest first. Step 3 leaves only the CC200 analysis. Step 4 shows all ten fields of the record, the same as `GET /analyses/{analysis_id}`. |
| **Actual result** | As expected. Participant 0050011: two analyses, Harvard-Oxford first, then CC200; with Atlas CC200 only the CC200 analysis; its detail showed the ten fields of memo 0013. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-07 Regenerate a past analysis

| Field | |
|---|---|
| **Use case** | Regenerate past result |
| **Steps** | 1. In History, open the CC200 analysis of 0050011. 2. Press Regenerate. |
| **Expected result** | A new record appears, pointing to the original (`reproduces_analysis_id`), with the same run ID. The dashboard shows the result is identical: same prediction, same confidence to 4 decimals, same calibrated flag. |
| **Actual result** | As expected. Regenerate of `e7842d068d2c` reported `Identical to the original.`; the new analysis `68e3628c940e` (10:29:10 UTC) has run `cf60f29e`, `control`, 0.5124, calibrated, and reproduces `e7842d068d2c`. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-08 Export an analysis record

| Field | |
|---|---|
| **Use case** | Export report |
| **Steps** | 1. Open one analysis. 2. Export as JSON. 3. Export as CSV. 4. Open both files. |
| **Expected result** | Files named `analysis_<id>.json` and `analysis_<id>.csv`. JSON holds the ten fields; CSV has one header row of the ten field names and one data row. Values match the record on screen. |
| **Actual result** | As expected. Export JSON and Export CSV saved `analysis_<id>.json` and `analysis_<id>.csv` with the ten fields and the values shown on screen. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-09 Models and calibration

| Field | |
|---|---|
| **Use case** | Supporting view: models and calibration (no use case in the diagram) |
| **Steps** | 1. Open Models. 2. Check each atlas. 3. Open the reliability diagram of one atlas. |
| **Expected result** | All four atlases with cross-validation and frozen-set metrics, the majority-class baseline, calibration error before and after calibration, and a reliability diagram. Figures equal the registry (`GET /models`) and the model cards in `docs/model_cards/`. |
| **Actual result** | The table showed the four atlases with run, CV accuracy, frozen accuracy, frozen AUC and ECE before and after calibration, equal to AC-11, and a reliability diagram for each atlas. The majority-class baseline (0.54 on the frozen set for every atlas) is not shown anywhere on the page. Bug #200. |
| **Status** | Fail |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

### TC-10 Exclusion log

| Field | |
|---|---|
| **Use case** | View exclusion log |
| **Steps** | 1. Open Exclusions. 2. Filter by gate = motion. 3. Find participant 0050039. |
| **Expected result** | 251 excluded participants, each with gate and reason. Step 2: 10 participants. Step 3: PITT, control, reason "func_mean_fd = 0.602 > 0.5". Same as `GET /exclusions` and `docs/reports/exclusion_log.csv`. |
| **Actual result** | As expected. 251 exclusions, each with gate and reason; Gate motion: 10; 0050039 PITT, control, `func_mean_fd = 0.602 > 0.5`. |
| **Status** | Pass |
| **Tester** | Aleesha Hayat |
| **Date** | 20 November 2026 |
| **Build** | `04f01b9` |

## Next round

Round 2 (Week 8) repeats every case on the build that fixes the three bugs, with the
dashboard cases cross-tested again and AC-09 and AC-10 included.
