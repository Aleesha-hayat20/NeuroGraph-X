# Week 1 plan
**Dates:** Monday 28 September to Sunday 4 October 2026
**Goal of the week:** the data is in hand and every open technical decision is closed.

## Assignments

| Member | Tasks | Closes the week when |
|---|---|---|
| **Aleesha** | Repository, folder structure and pinned environment. Download the ABIDE phenotypic CSV on its own and read its actual column names. Produce the metadata report: counts by group, site, sex, age band, and the distribution of the quality and motion variables. Pilot one atlas end to end and verify one correlation matrix, then pull the remaining three. Write the atlas decision memo. | Metadata report, one verified correlation matrix, atlas decision memo |
| **Laiba** | Verify the training environment on Kaggle or Colab, confirming PyTorch Geometric imports and a GPU is allocated. Train a graph neural network on a small standard graph dataset, not on ABIDE, to prove the training loop, logging and checkpointing work. Draft the model architecture note. | A training run that completes and checkpoints on any dataset, plus the architecture note |
| **Alishba** | Repository scaffolding, pytest, and GitHub Actions running tests on every push. Create the project board and open the entire four week backlog as issues, labelled and assigned. Draft the use-case and activity diagrams. | Green CI, populated board with the full backlog, two diagrams |

## Gate

- [ ] CI is green on the repository
- [ ] The phenotypic file is loaded and its real column names are documented
- [ ] One participant's correlation matrix has been computed and checked
- [ ] The atlas decision is written down with reasons
- [ ] The project board holds the full backlog, not only this week

## Interfaces agreed this week

| Contract | Producer | Consumer | Agreed |
|---|---|---|---|
| Participant record and quality flags | Aleesha | Laiba and Alishba | Wednesday 30 September |
| Graph object, with node count and atlas identifier | Aleesha | Laiba | Friday 2 October |
| Prediction response, with confidence and run id | Laiba | Alishba | Friday 2 October |
