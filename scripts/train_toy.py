"""Week 1 toy training loop. Proves training, logging, checkpointing and
reproducibility work BEFORE real ABIDE data arrives.

Usage:
    python train_toy.py                       # MUTAG, defaults
    python train_toy.py --dataset PROTEINS --epochs 150 --seed 7
"""
import argparse
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn import Dropout, Linear, ModuleList, ReLU, Sequential
from torch_geometric.datasets import FakeDataset, TUDataset
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool

from neurographx.m3_model.run_logger import log_run, new_run_id


# ----------------------------------------------------------------- utilities
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# --------------------------------------------------------------------- model
class GCN(torch.nn.Module):
    """N x GCNConv -> mean-pool readout -> MLP head."""

    def __init__(self, in_dim, hidden, num_classes, num_layers=3, dropout=0.5):
        super().__init__()
        dims = [in_dim] + [hidden] * num_layers
        self.convs = ModuleList(
            [GCNConv(dims[i], dims[i + 1]) for i in range(num_layers)]
        )
        self.head = Sequential(
            Linear(hidden, hidden), ReLU(), Dropout(dropout), Linear(hidden, num_classes)
        )
        self.dropout = dropout

    def forward(self, x, edge_index, batch):
        for conv in self.convs:
            x = F.relu(conv(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = global_mean_pool(x, batch)  # graph-level readout
        return self.head(x)  # logits


# ---------------------------------------------------------------- train/eval
def train_epoch(model, loader, optimizer, device):
    model.train()
    total = 0.0
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        loss = F.cross_entropy(model(data.x, data.edge_index, data.batch), data.y)
        loss.backward()
        optimizer.step()
        total += loss.item() * data.num_graphs
    return total / len(loader.dataset)


@torch.no_grad()
def evaluate(model, loader, device):
    """Returns (accuracy, logits) with logits in loader order."""
    model.eval()
    correct, all_logits = 0, []
    for data in loader:
        data = data.to(device)
        logits = model(data.x, data.edge_index, data.batch)
        correct += (logits.argmax(dim=1) == data.y).sum().item()
        all_logits.append(logits.cpu())
    return correct / len(loader.dataset), torch.cat(all_logits)


# ---------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="MUTAG")
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

    if args.dataset.upper() == "FAKE":
        # Offline synthetic graphs, no download. Labels are random, so accuracy
        # will hover near 50%. Use only to prove the plumbing works.
        dataset = FakeDataset(num_graphs=200, avg_num_nodes=30, avg_degree=4,
                              num_channels=7, num_classes=2)
    else:
        try:
            dataset = TUDataset(root="data/TUDataset", name=args.dataset)
        except Exception as e:  # noqa: BLE001
            raise SystemExit(
                f"Could not download {args.dataset}: {e}\n"
                "Turn Internet ON in Kaggle (Session options > Internet), "
                "or run with --dataset FAKE for an offline test."
            )
    print(f"{args.dataset}: {len(dataset)} graphs, "
          f"{dataset.num_node_features} node feats, {dataset.num_classes} classes")

    # Fixed, seeded 70/15/15 split (train / val / test)
    g = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(len(dataset), generator=g)
    n_train, n_val = int(0.7 * len(dataset)), int(0.15 * len(dataset))
    train_ds = dataset[perm[:n_train]]
    val_ds = dataset[perm[n_train:n_train + n_val]]
    test_ds = dataset[perm[n_train + n_val:]]

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size)

    model = GCN(dataset.num_node_features, args.hidden, dataset.num_classes,
                args.layers, args.dropout).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    run_id = new_run_id()
    ckpt_path = Path("checkpoints") / f"{args.dataset}_{run_id}.pt"
    ckpt_path.parent.mkdir(exist_ok=True)

    best_val, best_epoch = -1.0, 0
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(model, train_loader, optimizer, device)
        val_acc, _ = evaluate(model, val_loader, device)
        if val_acc > best_val:  # select checkpoint by VALIDATION accuracy
            best_val, best_epoch = val_acc, epoch
            torch.save({
                "state_dict": model.state_dict(),
                "in_dim": dataset.num_node_features,
                "num_classes": dataset.num_classes,
                "hidden": args.hidden,
                "layers": args.layers,
                "dropout": args.dropout,
            }, ckpt_path)
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d} | loss {loss:.4f} | val_acc {val_acc:.3f}")

    # ---- reload best checkpoint, evaluate on held-out test split
    ckpt = torch.load(ckpt_path, map_location=device)
    best_model = GCN(ckpt["in_dim"], ckpt["hidden"], ckpt["num_classes"],
                     ckpt["layers"], ckpt["dropout"]).to(device)
    best_model.load_state_dict(ckpt["state_dict"])
    test_acc, logits_a = evaluate(best_model, test_loader, device)

    # ---- reproducibility test: reload a second time, logits must be identical
    best_model2 = GCN(ckpt["in_dim"], ckpt["hidden"], ckpt["num_classes"],
                      ckpt["layers"], ckpt["dropout"]).to(device)
    best_model2.load_state_dict(torch.load(ckpt_path, map_location=device)["state_dict"])
    _, logits_b = evaluate(best_model2, test_loader, device)
    identical = torch.allclose(logits_a, logits_b, atol=1e-6)

    print(f"\nBest val acc {best_val:.3f} at epoch {best_epoch}")
    print(f"Test acc     {test_acc:.3f}")
    print(f"Reload reproduces identical predictions: {identical}")

    log_run({
        "run_id": run_id,
        "dataset": args.dataset,
        "atlas": None,  # filled in for ABIDE runs (e.g. "cc200")
        "seed": args.seed,
        "hyperparameters": {
            "hidden": args.hidden, "layers": args.layers, "dropout": args.dropout,
            "lr": args.lr, "batch_size": args.batch_size, "epochs": args.epochs,
        },
        "metrics": {"best_val_acc": best_val, "best_epoch": best_epoch,
                    "test_acc": test_acc},
        "checkpoint_path": str(ckpt_path),
        "reload_identical": identical,
    })
    print("Run logged. run_id =", run_id)


if __name__ == "__main__":
    main()
