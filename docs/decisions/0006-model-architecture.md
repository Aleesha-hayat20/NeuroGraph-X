# 0006. Baseline model architecture

**Status:** Accepted
**Date:** 2026-10-04
**Owner:** Laiba Afridi
**Related:** 0001 (atlases), 0002 (pipeline and strategy), 0004 (node counts), 0005 (frozen evaluation set)

> **Note on figures (2026-10-24).** The counts 871 participants and Harvard-Oxford 201
> below are Week 1 figures from `docs/reports/atlas_summary.md`, taken before the head
> motion gate was closed. The QC cohort the models train on is **861** (memo 0003), and in
> it **198** participants have flat Harvard-Oxford regions (memo 0007,
> `docs/reports/connectome_summary.md`). See the amendment of 2026-10-24 at the end.

## Context

Each participant is represented as one brain graph built from the connectome engine's
correlation matrices (pipeline `cpac`, strategy `filt_global`, see 0002 and
`docs/reports/atlas_summary.md`). The model must classify each graph as autism or control.
Decision 0004 already fixes one trained model per atlas. This record fixes everything else
about the baseline model, so the first real training run on CC200 can start without open
questions.

Every choice here is a baseline: simple, standard and defensible, not tuned for accuracy.

## Decision

### Input graph

| Element | Definition |
|---|---|
| Nodes | The regions of one atlas, N per graph |
| Node features | Row i of the N x N Fisher-z correlation matrix (N values per node) |
| Edges | Proportional threshold: keep the top 10% of off-diagonal pairs by absolute Fisher z, undirected |
| Edge weights | Not used in the baseline (binary edges) |
| Label | 1 = autism, 0 = control |

Thresholding is done in the model code, not in the connectome engine. The engine supplies
unthresholded matrices with the diagonal set to 0.

### Node counts and model size per atlas

Node counts are taken from `docs/reports/atlas_summary.md`, not from memory.

| Atlas | Nodes (N) = input dimension | Parameters (3 layers, 64 hidden) |
|---|---|---|
| AAL | 116 | about 20,100 |
| CC200 | 200 | about 25,500 |
| Harvard-Oxford | 111 | about 19,800 |
| Dosenbach 160 | 161 | about 23,000 |

Dosenbach "160" yields 161 regions in the downloaded files. The model always uses the
count found in the data, so the name and the node count differ by one.

### Model

1. **Three GCNConv layers** (Kipf and Welling, ICLR 2017), 64 hidden units, ReLU and
   dropout 0.5 after each.
2. **Global mean pooling** into one vector per participant.
3. **MLP head**: 64 -> 64 -> ReLU -> dropout -> 2 logits, cross-entropy loss.

### Training and selection

- Adam, learning rate 1e-3, batch size 32, 100 epochs, seed 42.
- The frozen evaluation set (0005) is removed before anything else.
- The remaining participants are split into train and validation, stratified by site and
  label together, with the seed recorded.
- Edge density, hyperparameters and the checkpoint are chosen on validation accuracy only.
- The frozen set is measured once, for the final model of each atlas.
- Every run writes its configuration and result to `runs/run_log.jsonl`.

### Checkpoint contents

state_dict, atlas, input dimension N, hidden size, layers, dropout, edge density and
run_id. Inference rebuilds exactly the graph and model used in training, and the API
selects the checkpoint by atlas (0004).

### Confidence

Softmax probability of the predicted class, between 0.5 and 1. It is uncalibrated until
the calibration work after the midterm and is returned with `calibrated: false`.

## Rationale

- **Correlation rows as features.** Each region is described by how it connects to every
  other region. This is the standard input in ABIDE graph-network work.
- **Proportional threshold.** Every participant gets the same number of edges, so graph
  density does not vary with scan noise or site. The density is a hyperparameter, which
  is why it is tuned on validation and kept out of the connectome engine.
- **Binary edges.** The baseline GCN call does not pass edge weights. Weighted edges are
  a planned comparison, not a baseline change.
- **GCNConv.** The most standard and best understood graph layer, stable on small
  datasets, and a clear reference for later variants such as GAT or GraphSAGE.
- **Three layers, 64 units.** Three hops already reach most of a graph at 10% density.
  Deeper GCNs over-smooth, making region representations indistinguishable. With 871
  participants the model is kept small, around 20,000 to 25,000 parameters, to limit
  overfitting.
- **Mean pooling.** Independent of region order and of N, and keeps the output scale
  comparable across atlases of different sizes.
- **Subject-level graphs, not a population graph.** Population-graph methods (for example
  Parisot et al., 2018) place evaluation participants inside the training graph. Classifying
  each participant's own brain graph keeps the frozen 100 completely outside training.

## Consequences

- The model assumes finite input. `atlas_summary.md` reports participants with
  zero-variance regions in every atlas (AAL 54, CC200 15, Harvard-Oxford 201,
  Dosenbach 160 46), which produce NaN rows. Training cannot start on an atlas until the
  connectome engine's NaN-handling memo fixes the rule. The graph builder raises an error
  on any NaN rather than repairing it silently.
- Mean pooling hides which regions drove a prediction. Interpretability is out of scope
  for the midterm.
- No site harmonisation in the baseline, so site differences may act as a confound.
- The validation split is small, so validation accuracy is noisy and optimistic when the
  best epoch is chosen from many. Validation accuracy is never reported as a result.
- GPU message passing in PyTorch Geometric is not bit-for-bit deterministic. Retraining
  with the same seed gives near-identical results. Reloading a saved checkpoint gives
  identical predictions.
- So far the training loop is verified on toy datasets (MUTAG, PROTEINS; runs 85bd9bb6,
  155be75c). The brain-shaped synthetic test, including a no-signal control, is the next
  verification step.

## Amendments

### 2026-10-12: training protocol and flat regions

- **Selection uses the committed 5-fold cross-validation** (`data/splits/cv5_folds.csv`,
  memo 0005), not a single train/validation split. Each fold picks its checkpoint on its own
  validation fold; settings (edge density, hidden size, ...) are compared on the mean
  cross-validation accuracy only.
- **One final model per atlas** is trained on the whole development pool (761) for the
  median best epoch across the folds, then measured **once** on
  `data/frozen/frozen_eval_100.csv`, logged and registered. `scripts/train_gnn.py` refuses a
  second frozen measurement for the same atlas unless `--allow-repeat` is given, and records it.
- **Reported metrics:** accuracy, balanced accuracy, AUC, confusion matrix, and the
  majority-class baseline (54 % on the frozen set: 54 control, 46 autism), so a model that
  predicts one class for everyone cannot look good.
- **Flat regions:** agreed with memo 0007. NaN from zero-variance regions is filled with 0
  ("no connection measured") in the loader (`fill_nan=0.0`), recorded in every run's
  configuration. The number of flat regions per participant is reported by group on the
  development pool, because flat regions follow scanner field of view and so track site.
- **Labels:** ABIDE DX_GROUP 1 (autism) becomes label 1, DX_GROUP 2 (control) becomes 0.

### 2026-10-24: Week 1 figures in this memo (Aleesha, agreed with Laiba)

- The Rationale's "871 participants" and the Consequences' flat-region count "Harvard-Oxford
  201" describe the Week 1 download: everyone who passed the rater checks, before the head
  motion gate (memo 0003, closed 6 October) removed 10 more.
- Current figures: QC cohort **861** (396 autism, 465 control); development pool 761 and
  frozen set 100 (memo 0005). Participants with flat regions in the 861: AAL 54, CC200 15,
  **Harvard-Oxford 198**, Dosenbach 160 46 (memo 0007). Only Harvard-Oxford changed.
- No decision in this memo depends on the difference: the model size argument holds for
  861 as for 871, and the flat-region rule is the one agreed in the 2026-10-12 amendment.
  The original text is left as written so the record of what was known on 4 October stays
  intact.
