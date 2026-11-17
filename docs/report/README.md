# Report v2.0: structure, owners and schedule

The FYP-I final report of NeuroGraph-X, in the structure of the FAST-NUCES FYP handbook. The
report is written in a shared document that is private to the team; the final PDF is added
to this folder once it has been submitted. This folder holds the agreed structure, the
chapter owners, the formatting rules and the schedule, and the software requirements
specification ([`srs.md`](srs.md)), which is a project document in its own right.

| | Date |
|---|---|
| Chapter drafts complete | Sunday 15 November 2026 |
| Draft to the supervisor (handbook pre-check) | Monday 16 November 2026 |
| Final PDF, with the supervisor's comments applied | Sunday 22 November 2026 |

## Owners

From work plan Section 9; front matter and references are shared.

| Part | Owner |
|---|---|
| Title page, signature sheets, contents and lists | Aleesha |
| Declarations | All three |
| Abstract (50 to 125 words) and executive summary | Aleesha, after every chapter is drafted |
| 1 Introduction | Aleesha |
| 2 Literature review and SRS | Aleesha (review), Alishba (SRS) |
| 3 Architecture and design | Alishba |
| 4 Implementation: 4.1 and 4.2 | Aleesha |
| 4 Implementation: 4.3 and 4.4 | Laiba |
| 4 Implementation: 4.5 (API) and 4.6 (dashboard) | Laiba, Alishba |
| 5 Testing and results: 5.1 to 5.4 (testing) | Aleesha |
| 5 Testing and results: 5.5 to 5.8 (results) | Laiba |
| 6 Conclusion and future work | All three, edited by Aleesha |
| References (IEEE style) | Each author adds the sources their chapter cites |
| Appendix A, user manual | Alishba |
| Appendices B to D | All three |

## Outline

**Front matter.** Title page; signature sheets; declarations; abstract; executive summary;
contents, list of figures, list of tables.

**1 Introduction.** 1.1 Background. 1.2 Problem statement. 1.3 Objectives. 1.4 Scope.
1.5 Why a graph neural network, and why fMRI. 1.6 Report outline.

**2 Literature review and software requirements.** 2.1 ABIDE and connectome-based
classification of autism. 2.2 Graph neural networks on brain networks. 2.3 Confounds: site,
motion and data quality. 2.4 Calibration and reproducibility in medical machine learning.
2.5 Software requirements specification (a summary of `srs.md`).

**3 Architecture and design.** 3.1 System architecture. 3.2 Use cases. 3.3 Data flow
(DFD levels 0 and 1). 3.4 Behaviour (activity diagram; sequence diagrams for running and for
regenerating an analysis). 3.5 Structure (class or component diagram). 3.6 Data design (ER
diagram, analysis record, registry entry, connectome store). 3.7 Algorithm design.
3.8 Design decisions (memos 0001 to 0014).

**4 Implementation.** 4.1 Data acquisition and quality control. 4.2 Connectome engine.
4.3 Model and training. 4.4 Calibration. 4.5 REST API and the analysis log. 4.6 Dashboard.

**5 Testing and results.** 5.1 Test strategy. 5.2 Automated tests and coverage.
5.3 Integrity check. 5.4 Manual system tests. 5.5 Model results. 5.6 Calibration results.
5.7 Performance and robustness. 5.8 Limitations.

**6 Conclusion and future work.** 6.1 Summary of the work. 6.2 Objectives achieved.
6.3 Future work in FYP-II.

**References.** IEEE style, numbered in order of first citation.

**Appendices.** A User manual. B API reference. C Manual test cases and round reports.
D Decision memos.

## Handbook formatting

- A4 paper; margins top 1.5 in, bottom 1.0 in, left 2.0 in, right 1.0 in.
- Body text Times New Roman 11 pt, line spacing 1.5; headings in Arial.
- Abstract between 50 and 125 words.
- References in IEEE style, numbered in order of first citation.
- Every figure and table numbered by chapter (Figure 3.2, Table 5.1) and cited in the text.

## Writing rules

- **Own words.** The handbook screens the report with Turnitin. Every borrowed idea is
  cited, and each chapter is written in its owner's own words rather than copied from
  papers, memos or the files in this repository.
- **One source for every number.** Figures quoted in the report come from the files that
  produced them: cohort counts from `docs/reports/metadata_report.md` and
  `docs/reports/exclusion_log.csv`, model results from `docs/reports/final_results.md` and
  `docs/model_cards/`, test counts and coverage from the CI run of the release commit.
- **Frozen-set results are quoted as measured once** (memo 0011). Cross-validation numbers
  are labelled as optimistic, because the configuration was selected on them.
- **The confound check is a limitation analysis** (`docs/reports/confound_check.md`), not
  a finding.
- **Research use only.** The system is not a diagnostic or medical device, and the report
  says so wherever predictions are shown.

## Source material in the repository, by chapter

| Chapter | Main sources |
|---|---|
| 1, 2 | work plan, `README.md`, cited literature; `srs.md` |
| 3 | `docs/design/`; memos 0007, 0008, 0012, 0013 |
| 4.1, 4.2 | memos 0001 to 0005 and 0007; `docs/reports/metadata_report.md`, `connectome_summary.md`, `connectome_verification.md` |
| 4.3, 4.4 | memos 0006, 0009, 0010, 0011; `docs/reports/tuning_selection.md`, `final_results.md`; `docs/model_cards/` |
| 4.5, 4.6 | memo 0013; the OpenAPI page at `/docs`; `dashboard/` |
| 5 | `docs/testing/`; CI runs; `scripts/check_integrity.py`; `docs/reports/confound_check.md` |
| 6 | work plan Section 10 (forward work into FYP-II) |
