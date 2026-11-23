# Release checklist

How a release of NeuroGraph-X is checked and tagged: `v1.0-fyp1` for the FYP-I final, and a
hotfix as `v1.0.1-fyp1` (work plan Section 8.8). The release manager, Aleesha Hayat, walks
through it on the demonstration machine, the MacBook named in the test plan. Each step says
what must be true before going on; a step that fails stops the release until it is fixed on
a branch and merged.

**Source:** FYP-I Final Work Plan, Section 2.2 (behind the demonstration), Week 8 gate and
evaluation window (Section 4), Section 8.8 (release and versioning).
**Record:** the result of each walk-through goes in that week's log under
`docs/progress/`.

## 1. Everything for the release is on `main`

1. Every pull request planned for the release is merged, and no open bug on the board breaks
   the demonstration.
2. Manual test round 2 is executed and recorded in `docs/testing/round_2.md`, and every bug
   it found is fixed or triaged as not affecting the demonstration.
3. The local copy matches GitHub:

   ```bash
   git checkout main
   git pull
   git status            # "Your branch is up to date with 'origin/main'", nothing to commit
   ```

## 2. CI is green on the commit to be tagged

```bash
gh run list --branch main --limit 3
gh run view <run id>            # the ID from the first line of the list
```

The latest run on `main` has a green tick (✓), and `gh run view` shows its three jobs
(`test`, `frontend`, `e2e`) passed. Note the statement coverage of `src/neurographx` printed by the
`test` job (`TOTAL` line); the report quotes it (work plan Section 6: 80 per cent or more on
M1 to M3 and the API).

## 3. The checks pass on the demonstration machine

Run from the repository root with the virtual environment active.

| Check | Command | Must show |
|---|---|---|
| Lint | `ruff check src scripts tests` | `All checks passed!` |
| Python tests, real data present | `pytest` | every test passed; none skipped, because the real-data performance test runs here |
| API on the fixture dataset | `python scripts/smoke_api.py --data fixtures` | `OK: the API runs on the fixtures dataset` |
| Integrity, fixture dataset | `python scripts/check_integrity.py --data fixtures` | `Integrity check passed` with `0 failed` |
| Integrity, real data | `python scripts/check_integrity.py` | `Integrity check passed` with `0 failed`; every registered model replayed within the tolerance |
| One prediction on the CPU | `python scripts/predict_one.py --participant 0050011 --atlas cc200 --expect control:0.5124` | `matches reference control:0.5124 (tolerance 0.001): True` |
| Analysis time (NFR-9) | `python scripts/benchmark_api.py` | every atlas `yes` for repeats identical and within 5 s; `docs/reports/performance.md` rewritten for this machine |
| Database view | `python scripts/build_db.py` | every run of the run log, the four registered models, and every analysis of the analysis log |
| Dashboard | `cd dashboard && npm ci && npm run lint && npm test && npm run build` | lint silent, every test passed, `built in` |

## 4. The demonstration runs on the real data

1. Start the API without `--reload` (`python -m uvicorn neurographx.api.main:app`) and the
   dashboard (`cd dashboard && npm run dev`). The API loads the model code at start-up, so
   the first analysis is not slower than the rest.
2. Walk through the eleven demonstration steps of work plan Section 2.1, from the cohort
   overview to the FYP-II tabs, with no slides.
3. The analyses created in this walk-through are the demonstration analyses. The real
   analysis log, `runs/analysis_log.jsonl`, is committed with them at release time
   (memo 0013, part 1), after `python scripts/check_integrity.py` passes again and
   `python scripts/build_db.py` reports them.

## 5. The documents are in place

`README.md`; `SETUP.md`, tested from a clean clone by a team member who did not write it;
`docs/api.md`; the four model cards in `docs/model_cards/`; `docs/testing/` (test plan,
manual test cases, the reports of rounds 1 and 2); `docs/reports/` (performance, confound
check, final results); decision memos `docs/decisions/0001` to `0016`; the diagrams in
`docs/design/`; the supervisor meeting log `docs/progress/meetings.md`; the user manual; and
`CHANGELOG.md`. The final report (Report v2.0) and the final deck are completed alongside.

## 6. Version and tag

1. The version is the same in `src/neurographx/__init__.py`, `pyproject.toml` and
   `dashboard/package.json` (and the two root entries of `dashboard/package-lock.json`):
   `1.0.0` for `v1.0-fyp1`, `1.0.1` for `v1.0.1-fyp1`. `GET /health` reports it.
2. In `CHANGELOG.md`, the heading `## [Unreleased]` becomes the release, with its date, for
   example `## [v1.0-fyp1] (23 November 2026)`.
3. These two changes and the analysis log reach `main` through the week's pull request, and
   CI passes on the merge commit (step 2).
4. Tag the merge commit on `main` with an annotated tag and push the tag:

   ```bash
   git checkout main && git pull
   git tag -a v1.0-fyp1 -m "NeuroGraph-X v1.0-fyp1: FYP-I final release"
   git push origin v1.0-fyp1
   ```

5. On GitHub, create a release from the tag, with the release section of `CHANGELOG.md` as
   its notes.

## 7. During the evaluation window

- No new features. The demonstration machine's operating system, Python and libraries are
  not updated (work plan, evaluation window).
- Before every demonstration: `python scripts/check_integrity.py` on the real data, then
  start the API and the dashboard as in step 4. The fallback video is on the laptop and on a
  USB drive.
- A bug that breaks the demonstration is fixed on a `hotfix/<issue>-<short description>`
  branch made from the tag, reviewed by another member, merged when CI passes, and released
  by walking through this checklist again as `v1.0.1-fyp1`.
