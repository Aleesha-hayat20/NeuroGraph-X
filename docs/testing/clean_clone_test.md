# Clean-clone test (#177)

**Tester:** Alishba Fayaz
**Date:** 24 November 2026
**Branch:** `feature/week8-release`, commit `a76b9a0`
**Machine:** Windows, PowerShell (Windows PowerShell 5.1) in VS Code
**Versions:** Python 3.14.7, Node v24.22.1, npm 11.19.1, Git 2.55.0.windows.5
**Folder:** `C:\Users\hp\Desktop\Project_clone\NGX-clean-clone`
**Real data (Section 6b):** phenotypic CSV downloaded earlier on this machine; connectomes folder from Aleesha.

## Summary

SETUP.md took a fresh clone to a running system in fixture mode and in real mode on Windows,
but not without help. Two steps needed a workaround (the pyyaml install on Python 3.14 and
the Windows forms of the `&&` and `NGX_PYTHON` commands). Three Python tests fail on Windows,
and the fix SETUP.md gives for them does not help on a fresh clone. Everything else matched
what SETUP.md says you should see: 55 dashboard tests, lint, build, the integrity checks on
both datasets, the CPU prediction (`control:0.5124`), the API smoke test and the end-to-end test (`1 passed`).

## Findings

Worst first.

| # | SETUP.md section | Problem | What I did to continue |
|---|---|---|---|
| 1 | 3 and 9 | 3 Python tests fail on Windows: `tests/test_fixture_data.py::test_generator_rebuilds_the_same_dataset`, `tests/test_fixture_data.py::test_time_series_are_reproducible_from_the_seed` and `tests/test_reliability.py::test_the_full_grid_logs_one_variant_run_per_job`, all SHA-256 mismatches on files the tests generate. The fix in Section 9 ("Hash tests fail on Windows": `git rm -r --cached -q .`, `git reset --hard`) gives the same three failures with the same fingerprints on a fresh clone, so its stated cause (a clone made before `.gitattributes` fixed line endings) does not fit. Section 3 also expects `453 passed, 1 skipped` (454 tests); 457 were collected. | Nothing changed; continued. |
| 2 | 1 and 3 | Section 1 allows "Python 3.11 or newer", but on Python 3.14 for Windows `pip install -r requirements-dev.txt` fails on `pyyaml==6.0.2` ("Microsoft Visual C++ 14.0 or greater is required") and installs nothing. Possible fixes: pin `pyyaml==6.0.3`, which has a Python 3.14 Windows build, or state Python 3.11 to 3.13. | Changed the pin to 6.0.3 in my clone only, installed, then restored `requirements.txt`. |
| 3 | 7 and 8 | Commands joined with `&&` (`cd dashboard && npm run dev` in Section 7; the dashboard checks in Section 8) fail in Windows PowerShell 5.1: "The token '&&' is not a valid statement separator in this version". No Windows form is given. | Ran the commands one by one. |
| 4 | 8 | The end-to-end command is given only in macOS/Linux form (`NGX_PYTHON="$PWD/../.venv/bin/python" npm run e2e`). The Windows note names the path but not the PowerShell syntax. | Used `$env:NGX_PYTHON = "<full path>\.venv\Scripts\python.exe"`, then `npm run e2e`. |
| 5 | 8 | `npm run e2e` stops with "http://127.0.0.1:8000/health is already used" when the API from Sections 5 or 7 is still running. SETUP.md does not say to stop the servers before the end-to-end test, and Section 9 does not list this message. With all servers stopped, the test passes (`1 passed`). | Stopped the other servers and ran it again. |
| 6 | 5 | The health link is written as "http://127.0.0.1:8000/health: it shows"; the colon becomes part of the link, so it opens the wrong address. | Typed the address without the colon. |
| 7 | 6 and 8 | `check_integrity.py` ends with warnings (2 on the real data, 1 on the fixtures) that SETUP.md does not mention; it only says the check must end with "passed" and "0 failed". On the fixtures, the output has no heading for section 2, and section 6 prints a heading with nothing under it. | None needed; both checks passed. |
| 8 | 4 | `npm ci` reports "3 moderate severity vulnerabilities" and suggests `npm audit fix`; SETUP.md does not say whether to act on it. | Did not run any audit fix. |
| 9 | 2 | SETUP.md's clone command clones `main`, where SETUP.md is still the Week 1 scaffold guide (209 tests, unzip the scaffold) until the Week 8 branch is merged. | Cloned feature/week8-release, as asked for #177. |
| 10 | 8 | Once, `npx playwright` was "not recognized" because `node_modules\.bin\playwright.cmd` was missing, although `@playwright/test` was installed and had worked earlier; the cause is unknown. Running `npm ci` again restored it. Not reproducible, so noted only. | Reran `npm ci`. |

## Log

One row per step, in the order I did them. Result is OK, Failed or Differed.

| # | SETUP.md section | What I ran or did | Result | Had to guess? | Exact message, or what differed from SETUP.md |
|---|---|---|---|---|---|
| 1 | 1. What you need | `git --version`, `python --version`, `node --version`, `npm --version` | OK | No | Git 2.55.0.windows.5, Python 3.14.7, Node v24.22.1, npm 11.19.1; all within the table |
| 2 | 2. Clone the repository | `git clone --branch feature/week8-release https://github.com/Aleesha-hayat20/NeuroGraph-X.git` (branch as asked for #177; SETUP.md's command clones `main`) | OK | No | Commit `a76b9a0` |
| 3 | 3. Install the Python side | `python3 -m venv .venv`, `.venv\Scripts\Activate.ps1`, `python -m pip install --upgrade pip` | OK | No | pip 26.2.1 → 26.3; prompt shows `(.venv)` |
| 4 | 3. Install the Python side | `pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu` | Differed | No | My mistake: SETUP.md marks this step "On Linux only"; I ran it on Windows. Installed `torch-2.11.0+cpu`, no effect on later steps. |
| 5 | 3. Install the Python side | `pip install -r requirements-dev.txt` | Failed | No | `ERROR: Failed building wheel for pyyaml` … `error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools"`. On Python 3.14.7 for Windows the pinned `pyyaml==6.0.2` has no ready-made package and needs a C++ compiler, so pip installed nothing from the list. |
| 6 | 3. Install the Python side (workaround) | Changed `pyyaml==6.0.2` to `pyyaml==6.0.3` in `requirements.txt` in my clone only, reran `pip install -r requirements-dev.txt`, then `git restore requirements.txt` | OK | Yes | Everything installed, including `pyyaml-6.0.3` and `torch-geometric-2.8.0.post1`. Workaround not in SETUP.md. |
| 7 | 3. Install the Python side | `pip install -e .` | OK | No | Installed `neurographx-1.0.0` |
| 8 | 3. Install the Python side | `pytest` | Failed | No | `3 failed, 453 passed, 1 skipped` (expected `453 passed, 1 skipped`, i.e. 454 tests; 457 were collected). Failed: `test_generator_rebuilds_the_same_dataset` (input_fingerprint `d463fb01fe5c…` instead of `9bf902d2b630…`), `test_time_series_are_reproducible_from_the_seed` (`f5a918888d40…` instead of `286bc764bcd5…`), `test_the_full_grid_logs_one_variant_run_per_job` (predictions sha256 `69b50da660d4…` instead of `26e31d031ce9…`). Git has `core.autocrlf=true`; `git ls-files --eol fixtures` shows no committed fixture file with CRLF on disk. |
| 9 | 9. If something goes wrong ("Hash tests fail on Windows") | `git rm -r --cached -q .`, `git reset --hard`, then `pytest` again | Failed | No | Same three tests, same fingerprints. The stated cause, a clone made before `.gitattributes` fixed line endings, does not apply to this fresh clone, and the fix does not resolve it. |
| 10 | 4. Install the dashboard | `cd dashboard`, `npm ci`, `npm test`, `cd ..` | OK | No | `Tests  55 passed (55)` as stated. `npm ci` also reported `3 moderate severity vulnerabilities`; I did not run any audit fix. |
| 11 | 5. Run the system in fixture mode | Terminal 1: `$env:NGX_DATA = "fixtures"`, `python -m uvicorn neurographx.api.main:app`; Terminal 2: `cd dashboard`, `npm run dev`; checked Overview, a CC200 run for 0090001, History | OK | No | Overview, the analysis and History as stated. The link "http://127.0.0.1:8000/health:" includes the colon and opens the wrong address. |
| 12 | 6b. Copy them from a team member | Copied `data/raw/Phenotypic_V1_0b_preprocessed1.csv` and `data/processed/connectomes/cpac_filt_global/` | OK | No | |
| 13 | 6. Check the real data | `python scripts/check_integrity.py` | OK | No | `Integrity check passed: 38 passed, 0 failed, 2 warnings.` The warnings (archived run 00252f2b has no checkpoint SHA-256; cv run df8dd345 has no out-of-fold file) are not explained in SETUP.md. |
| 14 | 6. Check the real data | `python scripts/predict_one.py --participant 0050011 --atlas cc200 --expect control:0.5124` | OK | No | `matches reference control:0.5124 (tolerance 0.001): True` |
| 15 | 8. The checks CI runs | `ruff check src scripts tests` | OK | No | `All checks passed!` |
| 16 | 8. The checks CI runs | `pytest --cov=src/neurographx --cov-report=term` | Failed | No | `3 failed, 454 passed` with the real data in place (expected `454 passed`): the same three tests as row 8. Coverage 92%. |
| 17 | 8. The checks CI runs | `python scripts/smoke_api.py --data fixtures` | OK | No | `OK: the API runs on the fixtures dataset` |
| 18 | 8. The checks CI runs | `python scripts/check_integrity.py --data fixtures` | OK | No | `Integrity check passed: 13 passed, 0 failed, 1 warnings.` (no calibration file for fixture run 1bf121a5). No heading for section 2; section 6 prints a heading with nothing under it. |
| 19 | 8. The checks CI runs | `cd dashboard && npm run lint && npm test && npm run build && cd ..` | Failed | No | `The token '&&' is not a valid statement separator in this version.` |
| 20 | 7. Run the system on the real data | New terminal without `NGX_DATA`: `python -m uvicorn neurographx.api.main:app`; second terminal: `cd dashboard`, `npm run dev` (run separately, `&&` does not work) | OK | No | As stated: `/health` shows `"data_mode": "real"`; Overview 1,112 participants, 861 included, 251 excluded; all four atlases have a registered model. No analysis was run in real mode. |
| 21 | 8. The checks CI runs | `cd dashboard`, `npm run lint` | OK | No | No problems reported |
| 22 | 8. The checks CI runs | `npm test` | OK | No | `Tests  55 passed (55)` |
| 23 | 8. The checks CI runs | `npm run build` | OK | No | `✓ built in 701ms` |
| 24 | 8. The checks CI runs | `npx playwright install chromium` | OK | No | No output (it also printed nothing when run again in row 28, so Chromium was presumably already installed) |
| 25 | 8. The checks CI runs | `NGX_PYTHON="$PWD/../.venv/bin/python" npm run e2e` | Failed | No | `The term 'NGX_PYTHON=$PWD/../.venv/bin/python' is not recognized…` (macOS/Linux syntax only) |
| 26 | 8. The checks CI runs | `$env:NGX_PYTHON = "C:\Users\hp\Desktop\Project_clone\NGX-clean-clone\.venv\Scripts\python.exe"`, `npm run e2e` | Failed | Yes | `Error: http://127.0.0.1:8000/health is already used, make sure that nothing is running on the port/url or set reuseExistingServer:true in config.webServer.` The API from an earlier section was still running. |
| 27 | 8. The checks CI runs | `npx playwright install chromium` (again, after stopping all servers) | Failed | No | `'playwright' is not recognized as an internal or external command, operable program or batch file.` `npm ls @playwright/test` showed `@playwright/test@1.65.0`, but `node_modules\.bin\playwright.cmd` did not exist, although `npm run e2e` had started Playwright earlier. Reran `npm ci` (Section 4); afterwards the file existed. |
| 28 | 8. The checks CI runs | `npx playwright install chromium`, `$env:NGX_PYTHON = "C:\Users\hp\Desktop\Project_clone\NGX-clean-clone\.venv\Scripts\python.exe"`, `npm run e2e` (all servers stopped) | OK | Yes (PowerShell form of the command) | `✓ 1 [chromium] › e2e\analysis_flow.e2e.js:5:1 › run an analysis and find it in History (5.8s)`, `1 passed (43.6s)` |