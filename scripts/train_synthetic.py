"""Week 1 brain-shaped synthetic test (NOT real data).
Rehearses the ABIDE protocol on synthetic brains: a frozen set drawn first and
never used for training or checkpoint selection, a stratified train/val split
of the remaining pool, checkpoint chosen by validation accuracy, then ONE
measurement on the frozen set. Run with --effect 0.0 as the null control.

Usage:
    python scripts/train_synthetic.py --effect 0.5
    python scripts/train_synthetic.py --effect 0.0
"""
import argparse
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch_geometric.loader import DataLoader
from train_toy import GCN, evaluate, set_seed, train_epoch

from neurographx.m3_model.run_logger import log_run, new_run_id
from neurographx.m3_model.synthetic_brain import make_dataset


def split_indices(graphs, frozen_n, val_frac, seed):
    """Frozen set first, then train/val from the remaining pool.
    Both splits stratified by site and label together."""
    ids = np.array([g.subject_id for g in graphs])
    strata = np.array([f"{g.site}_{int(g.y)}" for g in graphs])
    pool_idx, frozen_idx = train_test_split(
        np.arange(len(graphs)), test_size=frozen_n,
        stratify=strata, random_state=seed)
    train_idx, val_idx = train_test_split(
        pool_idx, test_size=val_frac,
        stratify=strata[pool_idx], random_state=seed + 1)
    # Leakage assertions: no subject in more than one split
    assert not set(ids[frozen_idx]) & set(ids[pool_idx]), "frozen leak"
    assert not set(ids[train_idx]) & set(ids[val_idx]), "train/val overlap"
    return train_idx, val_idx, frozen_idx


def main():
    p = argparse.ArgumentParser()
    # data
    p.add_argument("--effect", type=float, default=0.5)
    p.add_argument("--n_subjects", type=int, default=400)
    p.add_argument("--n_rois", type=int, default=200)
    p.add_argument("--density", type=float, default=0.10)
    p.add_argument("--frozen_n", type=int, default=100)
    p.add_argument("--val_frac", type=float, default=0.2)
    p.add_argument("--data_seed", type=int, default=0)
    # model (same defaults as train_toy.py)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--layers", type=int, default=3)
    p.add_argument("--dropout", type=float, default=0.5)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    graphs = make_dataset(n_subjects=args.n_subjects, n_rois=args.n_rois,
                          effect=args.effect, density=args.density,
                          seed=args.data_seed)
    train_idx, val_idx, frozen_idx = split_indices(
        graphs, args.frozen_n, args.val_frac, args.data_seed)
    train_ds = [graphs[i] for i in train_idx]
    val_ds = [graphs[i] for i in val_idx]
    frozen_ds = [graphs[i] for i in frozen_idx]
    for name, ds in [("train", train_ds), ("val", val_ds), ("frozen", frozen_ds)]:
        counts = np.bincount([int(g.y) for g in ds], minlength=2)
        print(f"{name:6s}: {len(ds):3d} subjects | control {counts[0]} | case {counts[1]}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)
    frozen_loader = DataLoader(frozen_ds, batch_size=args.batch_size)

    model = GCN(args.n_rois, args.hidden, 2, args.layers, args.dropout).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    run_id = new_run_id()
    ckpt_path = Path("checkpoints") / f"synthetic_e{args.effect}_{run_id}.pt"
    ckpt_path.parent.mkdir(exist_ok=True)

    best_val, best_epoch = -1.0, 0
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(model, train_loader, optimizer, device)
        val_acc, _ = evaluate(model, val_loader, device)
        if val_acc > best_val:  # checkpoint chosen on VALIDATION only
            best_val, best_epoch = val_acc, epoch
            torch.save({
                "state_dict": model.state_dict(),
                "in_dim": args.n_rois, "num_classes": 2,
                "hidden": args.hidden, "layers": args.layers,
                "dropout": args.dropout,
            }, ckpt_path)
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d} | loss {loss:.4f} | val_acc {val_acc:.3f}")

    # ---- ONE measurement on the frozen set, with the selected checkpoint
    ckpt = torch.load(ckpt_path, map_location=device)
    best_model = GCN(ckpt["in_dim"], ckpt["hidden"], ckpt["num_classes"],
                     ckpt["layers"], ckpt["dropout"]).to(device)
    best_model.load_state_dict(ckpt["state_dict"])
    frozen_acc, logits_a = evaluate(best_model, frozen_loader, device)
    pred_counts = np.bincount(logits_a.argmax(dim=1).numpy(), minlength=2).tolist()

    # ---- reproducibility: reload again, logits must match
    best_model2 = GCN(ckpt["in_dim"], ckpt["hidden"], ckpt["num_classes"],
                      ckpt["layers"], ckpt["dropout"]).to(device)
    best_model2.load_state_dict(torch.load(ckpt_path, map_location=device)["state_dict"])
    _, logits_b = evaluate(best_model2, frozen_loader, device)
    identical = torch.allclose(logits_a, logits_b, atol=1e-6)

    print(f"\nBest val acc     {best_val:.3f} at epoch {best_epoch}")
    print(f"Frozen-set acc   {frozen_acc:.3f}  (predicted control/case: {pred_counts})")
    print(f"Reload reproduces identical predictions: {identical}")

    log_run({
        "run_id": run_id,
        "dataset": "synthetic_brain",
        "atlas": f"synthetic{args.n_rois}",
        "seed": args.seed,
        "data_config": {
            "effect": args.effect, "n_subjects": args.n_subjects,
            "n_rois": args.n_rois, "density": args.density,
            "frozen_n": args.frozen_n, "val_frac": args.val_frac,
            "data_seed": args.data_seed,
        },
        "hyperparameters": {
            "hidden": args.hidden, "layers": args.layers, "dropout": args.dropout,
            "lr": args.lr, "batch_size": args.batch_size, "epochs": args.epochs,
        },
        "split_sizes": {"train": len(train_ds), "val": len(val_ds),
                        "frozen": len(frozen_ds)},
        "metrics": {"best_val_acc": best_val, "best_epoch": best_epoch,
                    "frozen_eval_acc": frozen_acc,
                    "frozen_pred_counts": pred_counts},
        "checkpoint_path": str(ckpt_path),
        "reload_identical": bool(identical),
    })
    print("Run logged. run_id =", run_id)


if __name__ == "__main__":
    main()
