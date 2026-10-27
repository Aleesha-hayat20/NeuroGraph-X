# NeuroGraph-X

A graph neural network platform for reliability-aware brain connectivity analysis in autism research.

Final Year Project 2026-27, Department of Computer Science, FAST-NUCES Peshawar.

| | |
|---|---|
| **Team** | Aleesha Hayat (23I-0682), Laiba Afridi (23I-6035), Alishba Fayaz (23P-0535) |
| **Supervisor** | Dr. Hafeez Anwar |
| **Dataset** | ABIDE Preprocessed, resting-state functional MRI |

## What this is

Published deep learning models for autism on the open ABIDE data report accuracies of about
70 per cent: 70 per cent for a deep neural network on 1,035 participants under 10-fold
cross-validation (Heinsfeld et al., 2018), and 70.4 per cent (AUC 0.75) for a graph
convolutional network on 871 participants, also under 10-fold cross-validation
(Parisot et al., 2018). Yet none of them is usable by a research team that did not build it.
Existing neuroimaging platforms process data but do not deploy trained models or issue
predictions, and no available tool reports how far a prediction depends on analysis
settings the user did not choose.

NeuroGraph-X turns that class of model into a working platform, and makes every prediction
it issues carry a reliability envelope.

**This is a research analysis tool. It does not diagnose, and it is not a medical device.**

References:
Heinsfeld, A. S., Franco, A. R., Craddock, R. C., Buchweitz, A., and Meneguzzi, F. (2018).
Identification of autism spectrum disorder using deep learning and the ABIDE dataset.
*NeuroImage: Clinical*, 17, 16 to 23. https://pubmed.ncbi.nlm.nih.gov/29034163/
Parisot, S., Ktena, S. I., Ferrante, E., Lee, M., Guerrero, R., Glocker, B., and Rueckert, D.
(2018). Disease prediction using graph convolutional networks: application to autism
spectrum disorder and Alzheimer's disease. *Medical Image Analysis*, 48, 117 to 130.
https://doi.org/10.1016/j.media.2018.06.001 (preprint: https://arxiv.org/abs/1806.01738)

## Modules

| Module | Layer | Function |
|---|---|---|
| M1 Ingestion and Quality Control | Data | Retrieval, validation, quality screening, exclusion logging |
| M2 Connectome Engine | Data | Region time series to weighted graph, four atlases |
| M3 GNN Model Service | Application | Trained classifier, inference, calibrated confidence |
| M4 Explanation Module | Application | Region and connection attribution |
| M5 Reliability Module | Application | Re-runs across seed, sample, atlas and site |
| M6 Report Generator | Presentation | Exportable reports with full run configuration |
| M7 Web Dashboard | Presentation | Participant selection, results, reliability display |

## Quick start

```bash
git clone <your repository url>
cd neurograph-x

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
pip install -e .

pytest                             # should pass before you change anything
```

## Week 1 workflow

```bash
python scripts/01_fetch_phenotypic.py     # download the phenotypic CSV, list its columns
python scripts/02_metadata_report.py      # build docs/reports/metadata_report.md
python scripts/03_pilot_atlas.py --n 5    # pilot one atlas, verify a correlation matrix
python scripts/04_fetch_all_atlases.py --limit 20   # optional trial on 20 participants
caffeinate -i python scripts/04_fetch_all_atlases.py  # all four atlases, everyone (macOS)
```

Run them in that order. Step 1 downloads one small CSV. Step 3 downloads region time
series for the pilot atlas only. Step 4 downloads all four atlases and writes
`docs/reports/atlas_summary.md`. It is resumable: if it stops, run it again.
`caffeinate -i` only keeps a Mac awake; on Linux or Windows drop it.

## Week 2 workflow

```bash
python scripts/05_apply_qc.py            # QC screen (memo 0003): cohort + exclusion log
python scripts/06_draw_frozen_set.py     # frozen 100 (drawn ONCE, memo 0005) + CV folds
python scripts/07_build_connectomes.py   # r and Fisher z for all four atlases, cached
python scripts/08_verify_connectomes.py  # independent recomputation of a sample
pytest                                   # includes the leakage assertion
```

Or `make week2`. Script 06 never redraws an existing frozen set; it only checks its hash.
Script 07 reuses stored matrices unless an input changed (`--force` rebuilds).

## Running without the real data (fixture mode)

The real data is about 1 GB and is not in the repository. A small **synthetic** dataset in
exactly the real file formats is (`fixtures/`, decision memo 0014). One setting switches
the API to it:

```bash
NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app --reload   # make api-fixtures
python scripts/smoke_api.py --data fixtures   # start the server and check it answers (CI runs this)
python scripts/build_fixtures.py --force      # regenerate after a file format changes
```

`/health` reports `"data_mode": "fixtures"`. Nothing measured on the fixture is a result.

> **Never request the `func_preproc` derivative.** The `rois_*` derivatives are small
> `.1D` text files. Everything else is a large `.nii.gz` volume.

## Repository layout

```
configs/          declared analysis choices, changed only through a decision memo
data/raw/         downloaded source data, not committed
data/interim/     intermediate artefacts, not committed
data/processed/   connectomes and features, not committed
data/frozen/      the frozen evaluation set, COMMITTED on purpose, never regenerated
data/splits/      QC cohort and training splits, COMMITTED, checked by the leakage test
fixtures/         small SYNTHETIC dataset in the real formats, for tests, CI and demos (memo 0014)
docs/decisions/   numbered decision memos, the reasoning behind every choice
docs/progress/    weekly plan and log, one folder per week
docs/reports/     generated reports and figures
src/neurographx/  the package, one subpackage per module
scripts/          numbered entry points, run in order
tests/            pytest suite, runs in CI on every push
```

## Conventions

- Anything that changes a result lives in `configs/` and is declared.
- Every analysis choice gets a numbered memo in `docs/decisions/`.
- Branches: `feature/<module>-<short-description>`, merged into `main` by pull request.
- Every pull request is read by at least one other member before merging.
- The test suite must pass before merging.
- Every training split lives in `data/splits/`. Nothing in `data/frozen/` is ever
  trained on; `tests/test_leakage.py` fails the build if it is.
