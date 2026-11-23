# Week 8 plan
**Work plan dates:** Monday 16 November to Sunday 22 November 2026; `v1.0-fyp1` is tagged on
`main` for the FYP-I final evaluation (window 23 November to 4 December).
**Goal of the week:** harden, document, rehearse. Bug fixes only.
**Source:** FYP-I Final Work Plan, Section 4 (Week 8 and the evaluation window).

Week 7 closed on Friday 20 November, so the Week 8 work runs past Sunday 22 November. Every
change is a bug fix, a test, documentation or the release itself; no feature is added after
the feature freeze of 15 November.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | Integrity check on the real data and the release checklist, `docs/release/checklist.md` (#174); tag `v1.0-fyp1` on `main` (#175). Final deck content, including the data structure and algorithm design slides (#176). Clean-clone test of the documentation with Alishba: `SETUP.md` rewritten so a fresh clone reaches a running dashboard, Alishba follows it alone, and every gap she hits is fixed (#137, #177). Test documentation with Laiba: cases, round reports, coverage figure (#178). Report Chapter 6 and Report v2.0 final (#172, #173). Two robustness and performance follow-ups found in review of PR #202: a connectome with missing or infinite values answers 503 with its own sentence, and the API loads the model code at start-up. Version 1.0.0. Plan, log, CHANGELOG, merge (#191); the presentation laptop frozen (#192); hotfix standby (#193) | The checklist is walked through on the demonstration machine with every check passing, and `v1.0-fyp1` is tagged with CI green |
| **Laiba** | Manual test round 2 on the dashboard, cross-testing Alishba's work (#179). Final metrics table frozen in the report and the model cards (#180). API reference final (#183). Fallback demo video with Alishba (#181). Test documentation with Aleesha (#178) | Round 2 dashboard cases recorded in `docs/testing/round_2.md`; the fallback video recorded |
| **Alishba** | Manual test round 2 on the API and data flows (#182). Final deck with the Gantt chart updated to show what was delivered against the plan (#184). User manual final, linked from the README (#185). Final diagrams in the report and the deck (#186). Clean-clone test from `SETUP.md` (#177). Supervisor meeting log and Sunday board screenshot (#189, #190) | Round 2 API checks recorded; the deck and the user manual committed |
| **All three** | Rehearse the demonstration three times, once on the presentation laptop (#188); fix any demonstration-breaking bug from round 2 (#187); apply the supervisor's report comments (#171) | Rehearsed three times; no open bug that breaks the demonstration |

## Gate (FYP-I Final Work Plan, Week 8: the 23 November deadline)

- `v1.0-fyp1` tagged on `main`; CI green.
- Report v2.0 final PDF, user manual, test report, model cards and deck in place.
- Manual test round 2 executed; no open bug that breaks the demonstration.
- Demonstration rehearsed three times; fallback video on the laptop and a USB drive.

## Evaluation window (23 November to 4 December)

No new features. A demonstration-breaking bug is fixed on a `hotfix/` branch, reviewed, and
re-tagged as `v1.0.1-fyp1` (`docs/release/checklist.md`, Section 7). The operating system,
Python and libraries on the presentation laptop are not updated. Rehearse once more the day
before the slot, and keep the weekly supervisor meeting.
