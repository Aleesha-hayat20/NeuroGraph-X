# Supervisor meetings

**Supervisor:** Dr. Hafeez Anwar, FAST-NUCES Peshawar.
**Source:** the signed paper log "FYP Supervisor Meeting Log - NeuroGraph-X" (each entry below
carries the supervisor's signature on the paper log) and its spreadsheet copy, kept by the
team in Google Sheets.

This file is the CLO5 evidence (supervisor meetings): one dated entry per meeting, in date
order, with the week of the work plan in the heading, and the attendees, decisions and actions
exactly as recorded in the paper log.

---

## 28 September 2026 (Week 1)

**Attendees:** Dr. Hafeez Anwar; Aleesha Hayat, Laiba Afridi

**Topics discussed**
- PC allocation form
- Ignite funding
- Discussion of Mid-1

**Decisions:** none written in the log.

**Actions:** none written in the log.

---

## 13 October 2026 (Week 3)

**Attendees:** Dr. Hafeez Anwar; Alishba Fayaz, Aleesha Hayat, Laiba Afridi

**Topics discussed**
- Slides presentation: meeting to show progress before the midterm.

**Decisions:** none written in the log beyond the actions below.

**Actions** (for the midterm presentation, defended 21 October)
- Include definitions for the frozen set and for 5-fold cross-validation (5F-CV).
- Add a graphical representation.
- Analyse the attributes of the dataset.

---

## Week 4 (19 to 25 October 2026): no meeting

No supervisor meeting took place this week.

---

## Week 5 (26 October to 1 November 2026): no meeting

No supervisor meeting took place this week.

---

## 3 November 2026 (Week 6)

**Attendees:** Dr. Hafeez Anwar; Laiba Afridi

**Topics discussed**
- Model and architecture review.

**Decisions:** none written in the log beyond the actions below.

**Actions** (backlog item W6-R1)
- Try running the model locally.
- Use sigmoid for the binary classification.
- Use the PC allotted in the FYP Lab.

---

## Week 7 (9 to 15 November 2026): no meeting

No supervisor meeting took place this week.

---

## 17 November 2026, first meeting (Week 8)

**Attendees:** Dr. Hafeez Anwar; Aleesha Hayat

**Topics discussed**
- Overview of the dataset: how it changed through the system, from the ABIDE Preprocessed
  cohort (1,112 participants), through quality control (861 included, 251 excluded), to
  the frozen evaluation set (100 participants) and the development pool (761 participants)
  used for 5-fold cross-validation.
- The columns and attribute fields of the original ABIDE Preprocessed phenotypic table.

**Decisions:** none written in the log.

**Actions:** none written in the log.

---

## 17 November 2026, second meeting (Week 8)

**Attendees:** Dr. Hafeez Anwar; Aleesha Hayat

**Topics discussed**
- The written remarks of the midterm jury, released on 17 November, including: "Moving the
  project from a strictly research domain to a more real-world application can be helpful."
- Options for a real-world repositioning of the project.

**Decisions**
- The repositioning that became memo 0015: the same disorder, data, models and modules,
  with a named user (a research group, hospital research unit or neuroimaging facility with
  its own resting-state fMRI) and, in FYP-II, the system accepting that user's data and
  reporting how far each result can be trusted on it. Approved by the supervisor.

**Actions:** none written in the log.

**Follow-up in the repository:** memo 0015 (`docs/decisions/0015-real-world-repositioning.md`),
accepted on 17 November; the jury remarks and their owners in
`docs/progress/midterm_jury_remarks.md` (issues #162, #163, #164).

---

## 19 November 2026 (Week 8)

**Attendees:** Dr. Hafeez Anwar; Laiba Afridi

**Topics discussed**
- Combining the four atlas models into an ensemble.

**Decisions**
- The team can proceed with the ensemble, averaging the predicted probabilities of the four
  models.

**Actions**
- Fix the combination rule and its cross-validation evidence in a decision memo before the
  frozen evaluation set is used (memo 0017).
- Build the ensemble script with its checks and tests, and measure the ensemble once on the
  frozen evaluation set.
- Add a comparative analysis slide to the final deck that references the results of
  Dong et al. (2025).

**Follow-up in the repository:** memo 0017 (`docs/decisions/0017-four-atlas-ensemble.md`)
proposed on 23 November and accepted on 24 November with the ensemble reported as one extra
row beside the four single-atlas models, which stay the main results and the models the
platform serves (PR #206). Ensemble script, integrity check section 8 and 20 tests (PR #208).
Measured once on the frozen set on 27 November, ensemble `a7f3095e`: accuracy 0.62 (95%
interval 0.52 to 0.71), balanced accuracy 0.616, AUC 0.680, against a majority baseline of
0.54 (PR #213, `docs/reports/ensemble.md`). The row on the Models page follows (Week 8 plan,
change of plan of 24 November).
