# 0015. Real-world repositioning of NeuroGraph-X

**Status:** Accepted. Approved by the supervisor, Dr. Hafeez Anwar, on 17 November 2026.
**Date:** 2026-11-17
**Owner:** Aleesha Hayat
**Related:** 0002 (pipeline strategy), 0003 (quality control), 0007 (connectome engine),
0010 (calibration), 0011 (tuning and the frozen set), 0013 (analysis log and API contract),
0014 (fixture data); the midterm jury remarks in `docs/progress/midterm_jury_remarks.md`
(board task #44, issue #000)

## Context

The written remarks of the FYP-I midterm jury (defence on 21 October 2026, remarks
released on 17 November 2026) include:

> "Moving the project from a strictly research domain to a more real-world application can
> be helpful."

In September the supervisor restructured the project into a deployed system for the same
reason: the jury expects a use case and an engineered system, not a research question
alone. That system now exists (M1, M2, M3 and the M7 dashboard), but every analysis starts
from an ABIDE participant ID: `POST /analyses` and `inference.predict` take a
`participant_id`, and the graph comes from the stored ABIDE connectomes. A lab with its own
scans has no way in, so the system still reads as a demonstration on a research dataset.

The remark is about who uses the system, on what data, and for what decision. It does not
ask for a different disorder or data type.

## Options considered

| Option | Meaning | Decision |
|---|---|---|
| A. Change the domain | A different disorder, data type or problem, for example a questionnaire-based screening app | Rejected. It discards the FYP-I system at the point where it is graded, and goes against the supervisor's direction to keep a GNN on fMRI for one disorder |
| B. Reword only | The same system, described in real-world terms | Rejected. FYP-II would show the same ABIDE-only demonstration again |
| C. Reposition and extend | The same disorder, data, models and modules; a named user; the system accepts that user's data and reports how far each result can be trusted on it | **Accepted** |

## Decision

### 1. Intended user and the decision supported

**User:** a research group, hospital research unit or neuroimaging facility that has
resting-state fMRI from its own scanner and wants an autism connectivity analysis without
building and validating a pipeline itself.

**Decision supported:** whether a participant's connectivity pattern is autism-like
according to a validated model, and how far that answer can be trusted on data from the
user's scanner. The uses are research screening of study cohorts and a second look at a
participant's data within a study. The output informs a researcher's next step in a study;
it never informs a clinical decision about a person. The research-use notice stays, and
the system remains a research tool, not a diagnostic or medical device.

### 2. Why this strengthens the planned contribution

The main obstacle to using an ABIDE-trained model elsewhere is data from a scanner it never
saw. The reliability module (M5) already plans a site axis: train with sites left out and
measure how results change. Under this decision that measurement becomes the first thing a
real user needs: the expected performance on an unseen scanner, shown with every result.

### 3. FYP-I: what changes before the final evaluation

No new features. Feature development closed on 15 November, and the demonstration must stay
stable.

- The three jury remarks are logged as issues with owners (#000, #000, #000;
  board task #44) and recorded in `docs/progress/midterm_jury_remarks.md`.
- `README.md` states who the system is for. The SRS (`docs/report/srs.md`, version 1.2)
  points to this memo in its product scope. The report outline (`docs/report/README.md`)
  adds the intended users to Chapter 1 and takes the FYP-II future work in Chapter 6 from
  Section 4 below.
- The final deck gets one slide, "From research to real-world use": the user, the decision
  supported, what already serves that user (calibrated confidence, model cards, the
  analysis log with regenerate and export, the integrity check, the research-use notice)
  and the FYP-II plan.
- The live demonstration is narrated as a lab analyst's workflow: check data quality,
  choose an atlas, read the calibrated result, regenerate it to confirm it is reproducible,
  export the record.

### 4. FYP-II: work in this order

This replaces the order of work plan Section 10 (forward work into FYP-II); every item of
Section 10 is kept.

1. **Upload of a user's own data (M1b).** One participant's preprocessed region time series
   for one of the four atlases, as a text table: one row per time point and one column per
   region, in the atlas's region order (AAL 116, CC200 200, Harvard-Oxford 111, Dosenbach
   160 with 161 columns, memo 0001). The graph is built at runtime by the same code as the
   ABIDE graphs (memo 0007); `inference.predict` already takes a graph-building function,
   so the model path does not change. Validation: the column count, at least 78 time points
   (the shortest scan in the training cohort), no missing values, and flat regions reported.
   Optional fields: the diagnosis label (stored only to evaluate the model on the lab's own
   data), mean framewise displacement, repetition time and scanner details. Raw scanner
   images are out of scope, because preprocessing takes hours per scan. Stretch goal:
   region extraction inside the platform from an already preprocessed 4D image in standard
   space, if the atlas files can be matched to the ones used for ABIDE Preprocessed.
2. **Data compatibility check.** Before a result is shown, a green, amber or red indicator
   of how far the uploaded data differ from the training data: preprocessing (C-PAC
   `filt_global`: band-pass 0.01 to 0.1 Hz with global signal regression, memo 0002),
   resting state rather than a task, age outside the training range (6.5 to 58 years),
   head motion, flat regions, and the distance of the connectome from the training
   distribution. If the repetition time is given, the platform can apply the band-pass
   filter itself. Global signal regression cannot be reproduced from region signals alone,
   so a missing one is flagged instead.
3. **Reliability envelope (M5) as trust information.** With every result: the spread
   across seeds, training samples and atlases, and the leave-site-out accuracy as the
   expected performance on an unseen scanner. Built on the FYP-I reliability skeleton.
4. **Report generator (M6).** A one-page PDF per analysis: result, calibrated confidence,
   compatibility, reliability, a model card summary, the settings and the research-use
   notice.
5. **Explanation (M4).** The regions and connections that drove a result, named by atlas
   region and brain network.
6. **Deployment and users.** Docker Compose packaging, a hosted instance, batch analysis of
   a cohort, and a small usability evaluation with three to five target users.

**FYP-II showcase.** A "new lab" demonstration on real data: one complete ABIDE site is
left out of training, and its participants are uploaded through M1b as if they came from a
new lab, showing the upload, the compatibility check and the site-level reliability. No
synthetic data is used for any result; the fixtures of memo 0014 stay for software tests.

## Consequences

- FYP-I scope, results and the frozen-set protocol (memo 0011) are unchanged.
- Uploaded data are never used for training, tuning or calibration, and are stored apart
  from the ABIDE data.
- Uploads are health data. No names or other identifiers are accepted or stored, a user can
  delete an upload after the analysis, and the research-use notice appears on every result.
- The API gains an upload path, and the analysis record gains its source (ABIDE or upload).
  Both are specified in an amendment to memo 0013 before they are built.
- SRS version 2.0 (FYP-II) adds the requirements for Section 4, with this memo as their
  source.
- The input contract of Section 4.1 goes into the user manual, so a lab knows what to
  prepare before uploading.

## Open items

- [ ] Title: keep the current title, add a subtitle (for example "a trust-aware analysis
      service for autism connectivity research") or revise it formally. To confirm with
      the supervisor, including whether a change needs department approval.
- [ ] Usability evaluation: who takes part (faculty, psychology or neuroscience contacts)
      and which questionnaire is used.
- [ ] FYP-II work plan and board iterations written from Section 4.
