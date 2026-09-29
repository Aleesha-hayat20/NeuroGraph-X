# NeuroGraph-X

A graph neural network platform for reliability-aware brain connectivity analysis in autism research.

Final Year Project 2026-27, Department of Computer Science, FAST-NUCES Peshawar.

| | |
|---|---|
| **Team** | Aleesha Hayat (23I-0682), Laiba Afridi (23I-6035), Alishba Fayaz (23P-0535) |
| **Supervisor** | Dr. Hafeez Anwar |
| **Dataset** | ABIDE Preprocessed, resting-state functional MRI |

## What this is

Published graph neural network models for autism connectivity reach around 80 per cent
accuracy on open data, yet none of them is usable by a research team that did not build it.
Existing neuroimaging platforms process data but do not deploy trained models or issue
predictions, and no available tool reports how far a prediction depends on analysis
settings the user did not choose.

NeuroGraph-X turns that class of model into a working platform, and makes every prediction
it issues carry a reliability envelope.

**This is a research analysis tool. It does not diagnose, and it is not a medical device.**

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
```

Run them in that order. Step 1 downloads one small CSV. Step 3 downloads region time
series for the pilot atlas only.

> **Never request the `func_preproc` derivative.** The `rois_*` derivatives are small
> `.1D` text files. Everything else is a large `.nii.gz` volume.

## Repository layout

```
configs/          declared analysis choices, changed only through a decision memo
data/raw/         downloaded source data, not committed
data/interim/     intermediate artefacts, not committed
data/processed/   connectomes and features, not committed
data/frozen/      the frozen evaluation set, COMMITTED on purpose
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
