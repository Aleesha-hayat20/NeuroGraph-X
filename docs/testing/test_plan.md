# Test plan

**Source:** FYP-I Final Work Plan, Section 6 (testing strategy) and Section 5.6 (manual test
case template). **Backlog:** #136.

NeuroGraph-X is tested at seven levels. Every level except the manual rounds and the
performance measurements runs in GitHub Actions (`.github/workflows/ci.yml`) on every push
to `main`, `develop` and `feature/**` branches and on every pull request. By the team's
rule (work plan Section 6), a pull request is merged to `main` only when all three CI jobs
pass.

## Levels

| Level | What it checks | Tool | Where it runs | Data |
|---|---|---|---|---|
| Unit and model | The functions of every module: ingestion and quality control (M1), the connectome engine (M2), the graph loader, training helpers, inference, calibration, tuning and the run logger (M3), the reliability skeleton (M5), the database import | pytest, CPU PyTorch | CI job `test`; `make test` | synthetic tables built in the tests, the fixture dataset |
| API | Every endpoint and every documented error (404, 409, 422, 503) of memo 0013, the analysis log, regenerate and export | pytest with FastAPI `TestClient`; `scripts/smoke_api.py` starts a real server | CI job `test` | the fixture dataset, copied to a temporary folder |
| Frontend unit | Dashboard components: participant table, result card, history, models and exclusions pages | Vitest, React Testing Library | CI job `frontend`; `npm test` in `dashboard/` | mocked API responses |
| End to end | Select a participant, run an analysis, read the result, find it in History | Playwright, fixture mode | CI job `e2e`; `npm run e2e` in `dashboard/` | the fixture dataset through the real API |
| Integrity | The registry, run log, checkpoints, split files, prediction and calibration files, connectome store and analysis log agree with the hashes recorded for them; each registered model reproduces its saved frozen-set predictions | `scripts/check_integrity.py` | CI job `test` on the fixture; on the real data before every demonstration | fixture in CI, real data locally |
| Performance and robustness | Analysis time on the Mac's CPU, repeated requests, every failure path returning the documented error | pytest with timing | locally, Week 7 (#139, #140); figures in Report Chapter 5.7 | real data |
| Manual system | Every FYP-I use case through the dashboard (TC-01 to TC-10) and the matching API checks (AC-01 to AC-14) | `docs/testing/manual_tests.md` | round 1 in Week 7, round 2 in Week 8, cross-tested | real data |

## Rules the tests enforce

- **No leakage.** `tests/test_leakage.py` fails if any participant of the frozen evaluation
  set (memo 0005) appears in a training split under `data/splits/`, and the training and
  reliability scripts run the same check before they train.
- **The frozen set never changes.** `tests/test_frozen_set.py` redraws it from its seed and
  compares it, and its hash, with the committed file.
- **The schema follows the run logger.** `tests/test_schema.py` fails if a run-log field
  has no database column.
- **The fixture is generated, not edited.** `tests/test_fixture_data.py` checks every
  fixture file against `fixtures/MANIFEST.json`.
- **Nothing measured on the fixture is a result** (memo 0014). Tests on the fixture check
  that the software works, not how well the model does.

## Running the tests

```bash
make lint                      # ruff on src, scripts and tests
make test                      # pytest
pytest --cov=src/neurographx --cov-report=term    # with coverage, as in CI
python scripts/smoke_api.py --data fixtures
python scripts/check_integrity.py --data fixtures # make integrity runs it on the real data
cd dashboard && npm test && npm run e2e
```

## Coverage

CI reports statement coverage of `src/neurographx` with `pytest-cov`. The work plan target
is 80 per cent or more on M1 to M3 and the API. The report quotes the figure from the CI
run of the release commit.

## Manual rounds

Cases are defined in `manual_tests.md` and recorded per round in `round_1.md` and
`round_2.md`. Each case is run by someone who did not build the feature under test. A
failed case gets a bug issue in the board's Bugs column, and its number is written in the
round file.
