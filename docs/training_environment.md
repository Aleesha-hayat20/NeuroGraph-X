# Training Environment Setup (L1)
In the repository these files live in scripts/. Run from the repository root, for example: python scripts/train_toy.py
Owner: Laiba Afridi · Date: 29 September 2026

## Platform
- [x] Kaggle  /  [ ] Colab
- Accelerator: GPU Tesla T4
- Internet: must be ON (Session options > Internet) for pip install and dataset download

## Install commands (exactly as run)
```
pip install torch_geometric
```

## Versions (output of `python check_env.py`)
```
Python          : 3.12.13
Platform        : Linux-6.12.90+-x86_64-with-glibc2.35
PyTorch         : 2.10.0+cu128
CUDA available  : True
GPU             : Tesla T4
CUDA version    : 12.8
PyG             : 2.8.0.post1
PyG import      : OK
scikit-learn    : 1.6.1
numpy / pandas  : 2.0.2 / 2.3.3
```

## Verification
- [x] `import torch_geometric` works
- [x] `torch.cuda.is_available()` is True
- [x] `python train_toy.py` completes and writes a checkpoint
- [x] Reloaded checkpoint gives identical predictions

## Toy training run (pipeline check, not a result)
- Dataset: MUTAG (188 graphs, 7 node features, 2 classes), seeded 70/15/15 split
- Model: 3-layer GCN, mean-pool readout, MLP head, seed 42, 100 epochs
- Loss fell from 0.69 to about 0.48
- Best val acc 0.750 (epoch 99), test acc 0.655
- Reload reproduces identical predictions: True
- run_id: 85bd9bb6 (logged in `runs/run_log.jsonl`)
- Accuracy is not meaningful here: MUTAG is about 66% one class and the val/test splits hold about 30 graphs each. The run only proves the training loop, logging and checkpointing work.

## Known issues / notes
- Kaggle blocks pip and dataset downloads unless Internet is switched on.
- If Internet is unavailable, `python train_toy.py --dataset FAKE` runs offline on synthetic graphs.
- When pasting files with `%%writefile`, make sure the first character of the file is not a stray `<` (caused a SyntaxError in `check_env.py` and `run_logger.py`).
- Kaggle working files can be lost when a session ends: use Save Version and download files.
