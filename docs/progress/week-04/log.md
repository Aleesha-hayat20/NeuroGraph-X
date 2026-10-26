# Week 4 log

## Monday 19 October, stand-up
**Closed since last time:** (fill in)
**Next:** midterm freeze and rehearsal Monday and Tuesday; defence Wednesday.
**Blocked:** nothing

## Thursday 22 October, stand-up
**Closed since last time:** midterm defended on Wednesday 21 October.
**Jury comments turned into issues:** currently pending
**Next:** production track, tasks in `plan.md`.
**Blocked:** nothing

## Entries

### 24 to 25 October (Aleesha)
- Repository state checked before starting: `main` at `c419421` (PR #38, torch and
  torch-geometric pinned in `requirements.txt`), after PRs #34 and #35 (CC200 baseline:
  CV accuracy 0.6728, frozen set measured once, 0.63 against a 0.54 majority baseline).
  Suite: 157 passing with PyTorch installed.
- **Fixture dataset (memo 0014).** `scripts/build_fixtures.py` writes `fixtures/`: 24
  synthetic participants in the 106-column phenotypic format; QC cohort 18, excluded 6,
  every gate and rule edge planted; frozen set 6; 12 in 5 folds; CC200 and Harvard-Oxford
  connectomes at their real sizes; a tiny registered CC200 model (1,770 parameters).
  Only the inputs are invented; every output is written by the project's own QC, splits,
  engine and run-logger code.
- **Fixture mode.** One setting, `NGX_DATA=fixtures`, through
  `src/neurographx/datasource.py`. `/health` reports `data_mode`. Pipeline and training
  scripts are unaffected by the setting.
- **Tests.** `tests/test_fixture_data.py` and `tests/test_datasource.py`: manifest
  intact, regeneration reproducible, real formats, real QC rules, splits re-derived,
  run-log hashes match the files, the checkpoint reproduces its recorded frozen result,
  the API serves the fixture. `scripts/smoke_api.py` starts uvicorn with the setting and
  checks the answers; added to CI.
- **Memos drafted:** 0011 (tuning grid of 12 per atlas, selection by mean CV balanced
  accuracy, freeze 2 November, CC200 second frozen measurement only as a declared repeat),
  0013 (append-only `runs/analysis_log.jsonl`, the analysis record, all endpoints, error
  contract, CORS), 0014 (fixtures).
- **Clean-up:** memo 0006 note and amendment (871 and 201 are Week 1 figures; QC cohort
  861; Harvard-Oxford 198); `atlas_summary.md` marked superseded; README's "around 80 per
  cent" replaced with Heinsfeld et al. 2018 (70 per cent) and Parisot et al. 2018
  (70.4 per cent), both checked against the papers.
- Tests: 198 passed.
- Pull request: (paste the PR link). CI run on `main` after merge: (paste the link).

## Decisions taken
- `docs/decisions/0011-tuning-protocol.md` (proposed)
- `docs/decisions/0013-analysis-log-and-api-contract.md` (proposed)
- `docs/decisions/0014-fixture-data.md` (proposed)

## Week close, Sunday 25 October
**Gate items met:** (tick in `plan.md` and list here)
**Gate items missed, and why:**
**Carried into next week:** memos 0011, 0013, 0014 to be accepted at the Thursday stand-up;
open items for Laiba (checkpoint paths through `datasource.checkpoint()`, class-weighted
loss, `repeat_reason`) and Alishba (dashboard against `make api-fixtures`, CORS).
**Board screenshot:** `board.png`
