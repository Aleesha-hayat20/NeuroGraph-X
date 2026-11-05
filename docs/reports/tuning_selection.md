# Tuning selection (memo 0011)

Grid `0011-v1`: edge density 0.05, 0.10, 0.20; class-weighted loss off/on; hidden 32, 64. 12 configurations per atlas, each one 5-fold cross-validation run on the 761 development participants.

Rule: highest mean CV balanced accuracy; within 0.005 of the best counts as tied, then fewest changes from the baseline (density 0.10, class weights off, hidden 64), then lower standard deviation across folds.
Runs logged before the freeze (2026-11-02T00:00:00+05:00) count; the frozen set is not read.

**The selected configuration's CV score is optimistic: it won a contest of twelve. It is reported next to the frozen-set result, never instead of it.**

## aal

| Density | Class weights | Hidden | Changes | Run | CV balanced (SD) | CV accuracy | CV AUC | Epochs | Selected | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | off | 32 | 2 | `be70b6e1` | 0.6699 (0.0136) | 0.6794 | 0.6893 | 33 |  |  |
| 0.05 | off | 64 | 1 | `f2753a4b` | 0.6654 (0.0120) | 0.6781 | 0.6986 | 27 |  |  |
| 0.05 | on | 32 | 3 | `144d079d` | 0.6702 (0.0270) | 0.6754 | 0.6923 | 35 |  |  |
| 0.05 | on | 64 | 2 | `d3611e1d` | 0.6819 (0.0124) | 0.6872 | 0.6969 | 24 | **selected** |  |
| 0.10 | off | 32 | 1 | `6c8293c2` | 0.6652 (0.0124) | 0.6754 | 0.6673 | 68 |  |  |
| 0.10 | off | 64 | 0 | `213699f4` | 0.6657 (0.0234) | 0.6728 | 0.6881 | 31 |  |  |
| 0.10 | on | 32 | 2 | `4b70082e` | 0.6719 (0.0335) | 0.6833 | 0.6875 | 52 |  |  |
| 0.10 | on | 64 | 1 | `6b974c7c` | 0.6643 (0.0201) | 0.6754 | 0.6811 | 24 |  |  |
| 0.20 | off | 32 | 2 | `bcbad3be` | 0.6590 (0.0257) | 0.6675 | 0.6712 | 68 |  |  |
| 0.20 | off | 64 | 1 | `9dce8666` | 0.6645 (0.0285) | 0.6728 | 0.6822 | 39 |  |  |
| 0.20 | on | 32 | 3 | `3c84b612` | 0.6487 (0.0313) | 0.6530 | 0.6622 | 46 |  |  |
| 0.20 | on | 64 | 2 | `b397c948` | 0.6637 (0.0393) | 0.6740 | 0.6760 | 47 |  |  |

12 of 12 configurations ran before the freeze. Selected: **density 0.05, class weights on, hidden 64**, CV run `d3611e1d` (balanced accuracy 0.6819, 1 configuration(s) within 0.005).

Final model, frozen set measured once: `python scripts/train_gnn.py --stage final --atlas rois_aal --epochs-from-cv d3611e1d`

## cc200

| Density | Class weights | Hidden | Changes | Run | CV balanced (SD) | CV accuracy | CV AUC | Epochs | Selected | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | off | 32 | 2 | `0b31ca07` | 0.6758 (0.0232) | 0.6807 | 0.6993 | 25 | tied |  |
| 0.05 | off | 64 | 1 | `c2516a5f` | 0.6777 (0.0226) | 0.6833 | 0.6960 | 30 | **selected** |  |
| 0.05 | on | 32 | 3 | `2d9f1c34` | 0.6700 (0.0226) | 0.6754 | 0.6980 | 56 |  |  |
| 0.05 | on | 64 | 2 | `5df4f9b8` | 0.6807 (0.0251) | 0.6859 | 0.7185 | 13 | tied |  |
| 0.10 | off | 32 | 1 | `5e08f86a` | 0.6535 (0.0153) | 0.6597 | 0.6743 | 28 |  |  |
| 0.10 | off | 64 | 0 | `23d68449` | 0.6689 (0.0152) | 0.6741 | 0.6948 | 21 |  |  |
| 0.10 | on | 32 | 2 | `456a9c1b` | 0.6643 (0.0087) | 0.6689 | 0.6859 | 21 |  |  |
| 0.10 | on | 64 | 1 | `e3eb7881` | 0.6756 (0.0250) | 0.6781 | 0.6890 | 35 |  |  |
| 0.20 | off | 32 | 2 | `23e49ae6` | 0.6314 (0.0220) | 0.6400 | 0.6407 | 28 |  |  |
| 0.20 | off | 64 | 1 | `39e59316` | 0.6606 (0.0329) | 0.6623 | 0.6647 | 34 |  |  |
| 0.20 | on | 32 | 3 | `ed298e01` | 0.6394 (0.0113) | 0.6439 | 0.6479 | 23 |  |  |
| 0.20 | on | 64 | 2 | `eb108912` | 0.6518 (0.0235) | 0.6531 | 0.6684 | 39 |  |  |

12 of 12 configurations ran before the freeze. Selected: **density 0.05, class weights off, hidden 64**, CV run `c2516a5f` (balanced accuracy 0.6777, 3 configuration(s) within 0.005).

CC200: a configuration other than the baseline was selected, so it is measured once more as a declared repeat: `python scripts/train_gnn.py --stage final --atlas rois_cc200 --epochs-from-cv c2516a5f --allow-repeat` (reason: post-tuning measurement per memo 0011).

## ho

| Density | Class weights | Hidden | Changes | Run | CV balanced (SD) | CV accuracy | CV AUC | Epochs | Selected | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | off | 32 | 2 | `6bf94e13` | 0.6681 (0.0202) | 0.6702 | 0.6783 | 48 | tied |  |
| 0.05 | off | 64 | 1 | `d1873b17` | 0.6704 (0.0266) | 0.6754 | 0.6799 | 49 | **selected** |  |
| 0.05 | on | 32 | 3 | `7758f64a` | 0.6720 (0.0187) | 0.6781 | 0.6798 | 42 | tied |  |
| 0.05 | on | 64 | 2 | `408ff48c` | 0.6695 (0.0249) | 0.6794 | 0.6793 | 32 | tied |  |
| 0.10 | off | 32 | 1 | `a9e28980` | 0.6580 (0.0164) | 0.6610 | 0.6624 | 33 |  |  |
| 0.10 | off | 64 | 0 | `2177020d` | 0.6500 (0.0299) | 0.6557 | 0.6556 | 38 |  |  |
| 0.10 | on | 32 | 2 | `7804bac4` | 0.6650 (0.0217) | 0.6676 | 0.6636 | 74 |  |  |
| 0.10 | on | 64 | 1 | `32089b8f` | 0.6432 (0.0411) | 0.6518 | 0.6641 | 22 |  |  |
| 0.20 | off | 32 | 2 | `d1239f70` | 0.6476 (0.0262) | 0.6505 | 0.6445 | 24 |  |  |
| 0.20 | off | 64 | 1 | `ce1e2b7f` | 0.6408 (0.0148) | 0.6465 | 0.6474 | 22 |  |  |
| 0.20 | on | 32 | 3 | `8bdb4cb7` | 0.6377 (0.0440) | 0.6465 | 0.6493 | 27 |  |  |
| 0.20 | on | 64 | 2 | `37b9208e` | 0.6420 (0.0176) | 0.6518 | 0.6462 | 29 |  |  |

12 of 12 configurations ran before the freeze. Selected: **density 0.05, class weights off, hidden 64**, CV run `d1873b17` (balanced accuracy 0.6704, 4 configuration(s) within 0.005).

Final model, frozen set measured once: `python scripts/train_gnn.py --stage final --atlas rois_ho --epochs-from-cv d1873b17`

## dosenbach160

| Density | Class weights | Hidden | Changes | Run | CV balanced (SD) | CV accuracy | CV AUC | Epochs | Selected | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | off | 32 | 2 | `93d85361` | 0.6419 (0.0431) | 0.6557 | 0.6574 | 30 |  |  |
| 0.05 | off | 64 | 1 | `f9f7e584` | 0.6507 (0.0218) | 0.6583 | 0.6443 | 69 | **selected** |  |
| 0.05 | on | 32 | 3 | `d7d2bf9e` | 0.6440 (0.0381) | 0.6583 | 0.6576 | 24 |  |  |
| 0.05 | on | 64 | 2 | `30f8cb33` | 0.6430 (0.0292) | 0.6465 | 0.6510 | 22 |  |  |
| 0.10 | off | 32 | 1 | `b3dab5d8` | 0.6330 (0.0269) | 0.6478 | 0.6281 | 24 |  |  |
| 0.10 | off | 64 | 0 | `eccad0f4` | 0.6244 (0.0256) | 0.6294 | 0.6285 | 72 |  |  |
| 0.10 | on | 32 | 2 | `29bfab52` | 0.6340 (0.0349) | 0.6465 | 0.6352 | 22 |  |  |
| 0.10 | on | 64 | 1 | `464bd9de` | 0.6214 (0.0323) | 0.6281 | 0.6363 | 16 |  |  |
| 0.20 | off | 32 | 2 | `26e8d95a` | 0.6150 (0.0254) | 0.6295 | 0.6231 | 24 |  |  |
| 0.20 | off | 64 | 1 | `e49b00a5` | 0.6200 (0.0316) | 0.6320 | 0.6316 | 22 |  |  |
| 0.20 | on | 32 | 3 | `ab8da145` | 0.6280 (0.0326) | 0.6373 | 0.6300 | 20 |  |  |
| 0.20 | on | 64 | 2 | `0309b3c4` | 0.6228 (0.0184) | 0.6281 | 0.6296 | 28 |  |  |

12 of 12 configurations ran before the freeze. Selected: **density 0.05, class weights off, hidden 64**, CV run `f9f7e584` (balanced accuracy 0.6507, 1 configuration(s) within 0.005).

Final model, frozen set measured once: `python scripts/train_gnn.py --stage final --atlas rois_dosenbach160 --epochs-from-cv f9f7e584`
