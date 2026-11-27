# Setting up NeuroGraph-X

This guide takes a fresh clone of the repository to a running dashboard. Follow it from the
top; every step says what you should see.

There are two ways to run the system:

- **Fixture mode** needs nothing beyond this repository. It runs the API and the dashboard
  on a small synthetic dataset in the real file formats (memo 0014). Use it to check a
  setup, to develop, and in CI. Nothing measured on it is a result.
- **Real mode** runs on the ABIDE Preprocessed data. The trained models are in the
  repository; the data is not (about 1 GB), so it is downloaded or copied once (Section 6).

Sections 1 to 5 are enough for fixture mode.

## 1. What you need

| Tool | Version | Check with |
|---|---|---|
| Git | any recent version | `git --version` |
| Python | 3.11 or newer; CI uses 3.11, and the team also uses 3.12 (macOS) and 3.14 (Windows) | `python3 --version` |
| Node.js and npm | Node.js 24 or newer; CI uses 24 (`dashboard/.nvmrc`) | `node --version` |

No GPU is needed. Training happened on Kaggle; serving runs on any laptop CPU (memo 0009).
The dashboard has been run on Node.js 24 (CI), 25 and 26.

On Windows, use `python` where this guide writes `python3`, and the activation command
given in Section 3. Every command in this guide is on its own line, so it runs unchanged in
Windows PowerShell; where PowerShell needs a different form, it is given next to it.

## 2. Clone the repository

```bash
git clone https://github.com/Aleesha-hayat20/NeuroGraph-X.git
cd NeuroGraph-X
```

Every command below is run from this folder, the repository root, unless it says otherwise.

## 3. Install the Python side

Create a virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Your prompt now starts with `(.venv)`. Activate it again in every new terminal.

**On Linux only**, install the CPU build of PyTorch first. The default Linux build also
downloads several gigabytes of GPU libraries that are never used:

```bash
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
```

Then, on every platform:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

Check the installation by running the test suite:

```bash
pytest
```

Without the real data the last line counts the tests that passed and ends with `1 skipped`;
it must not mention `failed`. The skipped test is the performance check on the real data; with the real data in place
(Section 6) it runs too, and nothing is skipped. Some tests guard the frozen evaluation set
on purpose, so if one fails, read its message before changing anything.

## 4. Install the dashboard

```bash
cd dashboard
npm ci
npm test
cd ..
```

`npm ci` installs the exact versions in `package-lock.json`. `npm test` ends with a
`Tests` line in which every test passed and none failed.

`npm ci` may also report a few moderate vulnerabilities. They are in the development tools
(the linter), not in the dashboard that reaches the browser: `npm audit --omit=dev` reports
`found 0 vulnerabilities`. Do not run `npm audit fix`, which rewrites `package-lock.json`.

## 5. Run the system in fixture mode

Open two terminals in the repository root and activate the virtual environment in the first.

**Terminal 1, the API:**

```bash
NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app
```

On Windows PowerShell, set the variable first: `$env:NGX_DATA = "fixtures"`, then run
`python -m uvicorn neurographx.api.main:app`. The server is ready when it prints
`Application startup complete.` Open <http://127.0.0.1:8000/health>, which shows
`"data_mode": "fixtures"`. The full API reference is at <http://127.0.0.1:8000/docs> and in
`docs/api.md`.

**Terminal 2, the dashboard:**

```bash
cd dashboard
npm run dev
```

Open <http://localhost:5173>. The footer of every page shows the API's status. On the
fixture dataset you should see:

- **Overview:** 24 participants, 17 included and 7 excluded by quality control.
- **Participants:** press Run for participant 0090001, choose CC200 and run the analysis.
  Of the fixture atlases only CC200 has both data and a model; the others are listed and
  cannot be chosen.
- **History:** the analysis you just ran, with Regenerate and Export.

Analyses made in fixture mode are written to `fixtures/runs/analysis_log.jsonl`, which git
ignores. Stop both servers with Ctrl+C.

## 6. Add the real data

These files are committed and need nothing: the four trained checkpoints (`checkpoints/`),
the model registry and run log (`runs/`), the frozen evaluation set (`data/frozen/`), the
quality-controlled cohort and the development folds (`data/splits/`).

Two inputs are not committed: the ABIDE phenotypic table and the connectomes of the four
atlases. Get them in one of two ways.

### 6a. Download and build them

```bash
python scripts/01_fetch_phenotypic.py              # the phenotypic table, into data/raw/
python scripts/03_pilot_atlas.py --n 5             # a small download that checks the connection
python scripts/04_fetch_all_atlases.py             # region time series of all four atlases
python scripts/07_build_connectomes.py             # connectome matrices, into data/processed/
```

Step 3 downloads the region time series of every participant for four atlases and takes the
longest. On a Mac, run it as `caffeinate -i python scripts/04_fetch_all_atlases.py` so the
computer does not sleep. It is resumable: if it stops, run the same command again and it
continues where it stopped. Never request the `func_preproc` derivative: the `rois_*` files
are small text files, everything else is a large volume.

Steps 2 to 4 also rewrite summary reports and figures under `docs/reports/`. If you did not
mean to change them, restore them with `git checkout -- docs/reports`.

### 6b. Or copy them from a team member

Copy these two items into the same places in your clone:

```
data/raw/Phenotypic_V1_0b_preprocessed1.csv
data/processed/connectomes/cpac_filt_global/        the folder, with its .npz and .json files
```

### Check the real data

```bash
python scripts/check_integrity.py
```

It checks that the registry, run log, checkpoints, data files and analysis log agree with
the hashes recorded for them, and replays each registered model on its saved frozen-set
predictions. It must end with `Integrity check passed` and `0 failed`. A few warnings are
expected and each says why, for example an archived run that is no longer served (two or
three on the real data, depending on the machine; one on the fixtures).

Then make one prediction on the CPU:

```bash
python scripts/predict_one.py --participant 0050011 --atlas cc200 --expect control:0.5124
```

The last line must read `matches reference control:0.5124 (tolerance 0.001): True`. The
script only predicts: it reads no labels and writes nothing.

## 7. Run the system on the real data

As in Section 5, without `NGX_DATA` (in PowerShell, open a new terminal, or run
`Remove-Item Env:NGX_DATA`). Terminal 1:

```bash
python -m uvicorn neurographx.api.main:app
```

Terminal 2:

```bash
cd dashboard
npm run dev
```

`/health` now shows `"data_mode": "real"`, and the Overview page shows 1,112 participants,
861 included and 251 excluded by quality control. All four atlases have a registered
model. At start-up the API loads the model code once, so the first analysis is as fast as
the ones after it.

Only the demonstration machine writes to the real analysis log, `runs/analysis_log.jsonl`
(memo 0013). On any other machine, explore in fixture mode, or delete the analyses you made
from that file before you commit.

## 8. The checks CI runs

GitHub Actions runs these on every push and pull request (`.github/workflows/ci.yml`). Run
them before you open a pull request:

```bash
ruff check src scripts tests
pytest --cov=src/neurographx --cov-report=term
python scripts/smoke_api.py --data fixtures
python scripts/check_integrity.py --data fixtures
cd dashboard
npm run lint
npm test
npm run build
cd ..
```

The end-to-end test drives a real browser through the dashboard on the fixture dataset, and
starts its own API and dashboard. **Stop the servers of Sections 5 and 7 first**, or it
stops with `http://127.0.0.1:8000/health is already used`. It needs the browser installed
once. `NGX_PYTHON` gives it the full path of the virtual environment's Python.

On macOS and Linux:

```bash
cd dashboard
npx playwright install chromium
NGX_PYTHON="$PWD/../.venv/bin/python" npm run e2e
cd ..
```

On Windows PowerShell:

```powershell
cd dashboard
npx playwright install chromium
$env:NGX_PYTHON = (Resolve-Path ..\.venv\Scripts\python.exe).Path
npm run e2e
cd ..
```

It ends with `1 passed`. The test plan, with every test level, is
`docs/testing/test_plan.md`.

## 9. If something goes wrong

| What you see | What to do |
|---|---|
| `Address already in use` when starting the API | Another server holds port 8000. Stop it (Ctrl+C in its terminal), or find it with `lsof -i :8000` on macOS and Linux. |
| The dashboard footer says the API cannot be reached | Start the API first (Section 5 or 7), then reload the page. |
| `npm ci` fails with an engine or syntax error | Check `node --version` shows 24 or newer. |
| A real-data endpoint answers 503 | A data file is missing. Run `python scripts/check_integrity.py`; its failed lines name the file. |
| `pip install -r requirements-dev.txt` fails with `Microsoft Visual C++ 14.0 or greater is required` | A pinned package has no ready-made build for your Python version on Windows, so pip tries to compile it. Use Python 3.11 to 3.14, which all have builds for the pinned versions, and upgrade pip first (Section 3). |
| Hash or fingerprint tests fail on Windows, in a clone made before 7 November 2026 | Files checked out before `.gitattributes` fixed line endings keep CRLF. Commit or stash your work, then run `git rm -r --cached -q .` and `git reset --hard` to check the files out again with LF endings. A fresh clone does not need this. |
| `http://127.0.0.1:8000/health is already used` from `npm run e2e` | The end-to-end test starts its own servers. Stop the API and the dashboard (Ctrl+C), then run it again. |
| `'playwright' is not recognized` | Run `npm ci` in `dashboard/` again; it restores the Playwright command. |
| `The token '&&' is not a valid statement separator` | Windows PowerShell 5.1 has no `&&`. Run the commands one per line, as this guide writes them. |
| `ModuleNotFoundError: neurographx` | The virtual environment is not active, or `pip install -e .` was skipped. |

Do not run `scripts/train_gnn.py --stage final` to check a setup. It measures the frozen
evaluation set, which happens once per atlas (memo 0011).

## Working on the repository

Each week's work goes on its own branch, opened as a pull request and merged into `main`
only when CI passes and that week's tasks run. Branch names follow
`feature/<module or issue>-<short description>`, `fix/<issue>-<short description>` and
`docs/<issue>-<short description>`. Releases are tagged as `v1.0-fyp1`, with hotfixes as
`v1.0.1-fyp1` (`docs/release/checklist.md`).
