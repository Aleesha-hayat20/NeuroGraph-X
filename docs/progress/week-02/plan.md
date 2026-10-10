# Week 2 plan
**Dates:** Monday 5 October to Sunday 11 October 2026
**Goal of the week:** the poster is submitted and everything the midterm demo needs is finished.

Monday and Tuesday: all three on the poster, submitted Tuesday evening. Tasks below run
from Wednesday.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | Connectome engine across all four atlases: correlation, Fisher transform, storage format, caching. Draw the frozen evaluation set of 100 participants, stratified by site and group together, seed recorded, committed as a file of subject identifiers. Leakage assertion as a pytest test that fails if any evaluation participant appears in a training split. Independently recompute a sample of matrices. | Matrices for four atlases, frozen set committed, leakage test passing in CI |
| **Laiba** | Train the first real model on one atlas, reproducible and measured on the frozen set. Run logging for every training run. Second atlas if time allows. | A model checkpoint, a measured number on the frozen set, a run log with entries |
| **Alishba** | Sequence diagram and updated system architecture diagram. Database schema for the run log and model registry. FastAPI skeleton with a health endpoint and a participants endpoint reading the real participant table. | Five diagrams complete, schema drafted, API returning real participant data |

## Gate (the real deadline)

- [ ] Poster submitted to SLATE
- [ ] Adjacency matrices exist for all four atlases
- [ ] The frozen 100 is committed and the leakage test passes in CI
- [ ] A model checkpoint exists and a number has been produced on the frozen set
- [ ] All five diagrams and the database schema are drafted

## Interfaces used this week

| Contract | Producer | Consumer | Where |
|---|---|---|---|
| Participant record and quality flags | Aleesha | Laiba, Alishba | `data/splits/qc_cohort.csv`, `docs/reports/exclusion_log.csv` |
| Graph object, with node count and atlas identifier | Aleesha | Laiba | `neurographx.m2_connectome.engine.load_atlas`, memo 0006 |
| Frozen set and training folds | Aleesha | Laiba | `data/frozen/frozen_eval_100.csv`, `data/splits/cv5_folds.csv` |
