# Manual system test cases

**Purpose:** checks a person carries out through the dashboard, one per use case, so that
every FYP-I use case is shown to work end to end on the real data. Automated tests (pytest,
Vitest, Playwright) check the parts; these check the whole system as a user meets it.
**Template:** FYP-I Final Work Plan, Section 5.6. **Backlog:** W5-17 (Alishba and Aleesha).
**Rounds:** round 1 in Week 7 (results in `docs/testing/round_1.md`), round 2 in Week 8
(`round_2.md`), each run by someone who did not build the feature under test
(cross-testing).

## How to use this file

- The cases below are the **definition**: what to do and what should happen. They change
  only when a use case changes.
- Each round copies the cases it runs into `round_N.md` and fills in **Actual result**,
  **Status**, **Tester**, **Date** and **Build**. A failed case gets a bug issue on the
  board, and its number goes in the Actual result.
- **Status** is one of: `Pass`, `Fail`, `Blocked` (could not be run, for example the
  feature is not merged yet), `Not run`.
- **Build** is the short commit hash the dashboard and API were running
  (`git log --oneline -1`).
- Expected results are written for the **real ABIDE data** (1,112 participants). The same
  steps work in fixture mode (`NGX_DATA=fixtures`), where the counts are those in
  `fixtures/README.md`; a fixture run is a rehearsal, not a round result.
- Use case names follow the FYP-I use case diagram. If the diagram's numbering changes,
  update the **Use case** row, not the test ID.

## Template

| Field | |
|---|---|
| **ID** | TC-NN |
| **Use case** | the use case this case demonstrates |
| **Preconditions** | what must be true before step 1 |
| **Steps** | numbered actions, one per line |
| **Expected result** | what the tester must see; numbers where there are numbers |
| **Actual result** | filled in during a round |
| **Status** | filled in during a round |
| **Tester** | filled in during a round |
| **Date** | filled in during a round |
| **Build** | filled in during a round |

Common preconditions for every case: the API is running on the real data
(`make api`, `/health` shows `"data_mode": "real"`), the dashboard is open in a browser,
and the page shows the research-use notice.

---

## TC-01 Cohort overview

| Field | |
|---|---|
| **ID** | TC-01 |
| **Use case** | View cohort overview |
| **Preconditions** | Common preconditions |
| **Steps** | 1. Open the Overview page. 2. Read the totals. 3. Read the quality-gate counts. 4. Look at the charts. |
| **Expected result** | 1,112 participants in the table; 861 retained; 251 excluded. Excluded by first gate: rater 241, motion 10, completeness 0. Retained by split: 100 frozen, 761 development. Charts by group and site agree with these totals. Same numbers as `GET /cohort/summary`. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-02 Browse and filter participants

| Field | |
|---|---|
| **ID** | TC-02 |
| **Use case** | Browse and filter participants |
| **Preconditions** | Common preconditions |
| **Steps** | 1. Open Participants. 2. Filter site = NYU. 3. Add quality status = included. 4. Add group = autism. 5. Clear all filters. |
| **Expected result** | Step 2: 184 NYU participants. Step 3: 172. Step 4: 74. Step 5: all 1,112 again. The header totals (1,112 / 861 / 251) do not change while filtering. Each row shows a quality badge. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-03 Excluded participant cannot be analysed

| Field | |
|---|---|
| **ID** | TC-03 |
| **Use case** | Inspect an excluded participant |
| **Preconditions** | Common preconditions |
| **Steps** | 1. Open Participants. 2. Select participant 0050002 (PITT). |
| **Expected result** | Status "excluded", gate "rater", reasons "qc_rater_1 = fail", "qc_func_rater_2 = fail", "qc_func_rater_3 = fail". The Run button is disabled. No analysis is created (History unchanged). |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-04 Run an analysis

| Field | |
|---|---|
| **ID** | TC-04 |
| **Use case** | Run an analysis |
| **Preconditions** | Common preconditions; a model is registered for CC200 (`GET /atlases`) |
| **Steps** | 1. Select participant 0050011 (frozen set). 2. Open Analysis; check the four atlases are offered. 3. Choose CC200. 4. Run. |
| **Expected result** | Four atlases listed, each showing whether a model is registered. The result shows the prediction (autism or control), the confidence (0.5 to 1), the calibrated flag, the atlas, the model's run ID and a new 12-character analysis ID, with the research-use notice. A note says the participant is in the frozen evaluation set. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-05 Same participant on a second atlas

| Field | |
|---|---|
| **ID** | TC-05 |
| **Use case** | Run an analysis on another atlas |
| **Preconditions** | TC-04 passed; a model is registered for a second atlas |
| **Steps** | 1. Keep participant 0050011. 2. Choose a second atlas with a registered model. 3. Run. |
| **Expected result** | A second result with a different analysis ID and that atlas's run ID. Choosing an atlas without a registered model shows "No model is registered for atlas '...'" and creates no analysis. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-06 Analysis history

| Field | |
|---|---|
| **ID** | TC-06 |
| **Use case** | View analysis history |
| **Preconditions** | TC-04 and TC-05 passed |
| **Steps** | 1. Open History. 2. Filter by participant 0050011. 3. Filter by atlas CC200. 4. Open one record. |
| **Expected result** | Both analyses listed, newest first. Step 3 leaves only the CC200 analysis. Step 4 shows all ten fields of the record, the same as `GET /analyses/{analysis_id}`. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-07 Regenerate a past analysis

| Field | |
|---|---|
| **ID** | TC-07 |
| **Use case** | Regenerate an analysis |
| **Preconditions** | TC-06 passed; regenerate is merged (backlog W6-06, W7-17) |
| **Steps** | 1. In History, open the CC200 analysis of 0050011. 2. Press Regenerate. |
| **Expected result** | A new record appears, pointing to the original (`reproduces_analysis_id`), with the same run ID. The dashboard shows the result is identical: same prediction, same confidence to 4 decimals, same calibrated flag. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-08 Export an analysis record

| Field | |
|---|---|
| **ID** | TC-08 |
| **Use case** | Export an analysis |
| **Preconditions** | TC-06 passed; export is merged (backlog W6-07) |
| **Steps** | 1. Open one analysis. 2. Export as JSON. 3. Export as CSV. 4. Open both files. |
| **Expected result** | Files named `analysis_<id>.json` and `analysis_<id>.csv`. JSON holds the ten fields; CSV has one header row of the ten field names and one data row. Values match the record on screen. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-09 Models and calibration

| Field | |
|---|---|
| **ID** | TC-09 |
| **Use case** | View models |
| **Preconditions** | Common preconditions; final models registered (backlog W6-04) |
| **Steps** | 1. Open Models. 2. Check each atlas. 3. Open the reliability diagram of one atlas. |
| **Expected result** | All four atlases with cross-validation and frozen-set metrics, the majority-class baseline, calibration error before and after calibration, and a reliability diagram. Figures equal the registry (`GET /models`) and the model cards in `docs/models/`. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

## TC-10 Exclusion log

| Field | |
|---|---|
| **ID** | TC-10 |
| **Use case** | View exclusions |
| **Preconditions** | Common preconditions |
| **Steps** | 1. Open Exclusions. 2. Filter by gate = motion. 3. Find participant 0050039. |
| **Expected result** | 251 excluded participants, each with gate and reason. Step 2: 10 participants. Step 3: PITT, control, reason "func_mean_fd = 0.602 > 0.5". Same as `GET /exclusions` and `docs/reports/exclusion_log.csv`. |
| **Actual result** | |
| **Status** | Not run |
| **Tester** | |
| **Date** | |
| **Build** | |

---

## Coverage

| FYP-I demonstration step (work plan 2.1) | Case |
|---|---|
| 1 Cohort overview | TC-01 |
| 2 Participants, filters, excluded participant | TC-02, TC-03 |
| 3 Four atlases offered | TC-04 |
| 4 Run an analysis | TC-04 |
| 5 Second atlas | TC-05 |
| 6 History | TC-06 |
| 7 Regenerate | TC-07 |
| 8 Export | TC-08 |
| 9 Models | TC-09 |
| 10 Exclusions | TC-10 |
| 11 FYP-II tabs | to add in Week 7 with the tabs (W7 dashboard features) |
