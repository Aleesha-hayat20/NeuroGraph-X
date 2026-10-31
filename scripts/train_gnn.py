"""Train and evaluate the baseline GNN on real ABIDE connectomes (L3, L4).

Two stages, run separately on purpose:

  cv     Five-fold cross-validation on the development pool (data/splits/cv5_folds.csv).
         Use it as often as you like to compare settings (density, hidden size, ...).
         It never builds a frozen-set graph. It also writes the out-of-fold
         probabilities, one per development participant, to runs/oof/ (input to
         calibration, memo 0010) and records their file hash in the run log.

  final  Trains ONE model on the whole development pool, for the number of epochs the
         cross-validation chose, then measures it ONCE on the frozen evaluation set
         (data/frozen/frozen_eval_100.csv), logs the run and registers the model.
         Refuses to run a second time for the same atlas unless --allow-repeat is
         given, and then records that it was a repeat.

Usage (from the repository root):
    python scripts/train_gnn.py --stage cv
    python scripts/train_gnn.py --stage cv --class-weighted --tuning-grid 0011-v1   (memo 0011)
    python scripts/train_gnn.py --stage final --epochs-from-cv <cv run_id>

The final stage takes every setting (including class weighting) from the CV run it
is given, and saves the frozen-set probabilities per participant to
runs/frozen_predictions/ (memo 0010), so calibration never needs a second measurement.
"""
import argparse
import statistics
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from torch_geometric.loader import DataLoader

from neurographx.m1_ingestion.splits import assert_no_leakage, read_ids
from neurographx.m2_connectome.engine import sha256_file
from neurographx.m3_model.data import (
    build_graphs,
    flat_region_summary,
    load_connectomes,
    short_atlas_name,
)
from neurographx.m3_model.model import GCN, model_from_checkpoint
from neurographx.m3_model.oof import (
    fold_rows,
    frozen_predictions_path,
    oof_path,
    write_frozen_predictions,
    write_oof,
)
from neurographx.m3_model.run_logger import (
    get_run,
    log_run,
    new_run_id,
    read_runs,
    register_model,
)
from neurographx.m3_model.training import class_weights, evaluate, set_seed, train_epoch

FOLDS_FILE = Path("data/splits/cv5_folds.csv")
FROZEN_FILE = Path("data/frozen/frozen_eval_100.csv")
DATASET = "ABIDE"


def code_version() -> str | None:
    """git commit, or the contents of a COMMIT file when the repo was copied without .git."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        commit = Path("COMMIT")
        return commit.read_text().strip() if commit.exists() else None


def fit(train_graphs, val_graphs, args, device, ckpt_path=None):
    """Train; if val_graphs is given, keep the best epoch by validation accuracy."""
    set_seed(args.seed)
    model = GCN(train_graphs[0].x.shape[1], args.hidden, 2, args.layers, args.dropout).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    # memo 0011: weights from this training fold's labels only, never validation or frozen
    weight = class_weights([int(g.y) for g in train_graphs]) if args.class_weighted else None
    train_loader = DataLoader(train_graphs, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_graphs, batch_size=args.batch_size) if val_graphs else None
    best = {"val_acc": -1.0, "epoch": 0, "state": None}
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(model, train_loader, optimizer, device, weight)
        if val_loader is not None:
            val_acc, _ = evaluate(model, val_loader, device)
            if val_acc > best["val_acc"]:
                best = {"val_acc": val_acc, "epoch": epoch,
                        "state": {k: v.detach().cpu().clone()
                                  for k, v in model.state_dict().items()}}
        if epoch == 1 or epoch % 20 == 0:
            extra = f" | val_acc {val_acc:.3f}" if val_loader is not None else ""
            print(f"    epoch {epoch:3d} | loss {loss:.4f}{extra}")
    if val_loader is not None:
        model.load_state_dict(best["state"])
    return model, best


def scores(model, graphs, device, batch_size):
    """Accuracy, balanced accuracy, AUC, confusion matrix and majority baseline."""
    loader = DataLoader(graphs, batch_size=batch_size)
    acc, logits = evaluate(model, loader, device)
    y = np.array([int(g.y) for g in graphs])
    prob_autism = torch.softmax(logits, dim=1)[:, 1].numpy()
    pred = logits.argmax(dim=1).numpy()
    majority = max(np.mean(y == 0), np.mean(y == 1))
    return {
        "n": int(len(y)),
        "accuracy": round(float(acc), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
        "auc": round(float(roc_auc_score(y, prob_autism)), 4) if len(set(y)) == 2 else None,
        "majority_baseline": round(float(majority), 4),
        "confusion_tn_fp_fn_tp": confusion_matrix(y, pred, labels=[0, 1]).ravel().tolist(),
        "predicted_autism": int(pred.sum()),
    }, logits


def hyperparameters(args) -> dict:
    return {"hidden": args.hidden, "layers": args.layers, "dropout": args.dropout,
            "lr": args.lr, "batch_size": args.batch_size, "epochs": args.epochs,
            "class_weighted": bool(args.class_weighted)}


def data_config(args, cset) -> dict:
    return {"atlas_key": args.atlas, "density": args.density, "fill_nan": args.fill_nan,
            "folds_file": str(FOLDS_FILE), "folds_sha256": sha256_file(FOLDS_FILE),
            "frozen_file": str(FROZEN_FILE), "frozen_sha256": sha256_file(FROZEN_FILE),
            "connectome_engine": cset.manifest.get("engine_version"),
            "connectome_sha256": cset.manifest.get("output_sha256"),
            **({"tuning_grid": args.tuning_grid} if args.tuning_grid else {})}


def stage_cv(args, cset, folds, frozen, device):
    print("\n== Cross-validation (development pool only; no frozen-set graph is built) ==")
    print("Flat regions by group (development pool):", flat_region_summary(cset, folds))
    started = time.perf_counter()
    graphs = build_graphs(cset, folds, args.density, args.fill_nan)
    fold_of = folds["fold"].to_numpy()
    per_fold, oof_parts = [], []
    for k in sorted(set(fold_of)):
        fold_started = time.perf_counter()
        train = [g for g, f in zip(graphs, fold_of) if f != k]
        val = [g for g, f in zip(graphs, fold_of) if f == k]
        print(f"  fold {k}: train {len(train)} | validation {len(val)}")
        model, best = fit(train, val, args, device)
        metrics, logits = scores(model, val, device, args.batch_size)
        metrics["best_epoch"] = best["epoch"]
        metrics["seconds"] = round(time.perf_counter() - fold_started, 1)
        per_fold.append(metrics)
        # out-of-fold: the probabilities this fold's model gave the participants it never saw
        oof_parts.append(fold_rows(folds[fold_of == k], int(k),
                                   [int(g.y) for g in val],
                                   torch.softmax(logits, dim=1)[:, 1].numpy()))
        print(f"  fold {k}: best epoch {best['epoch']} | {metrics}")

    def summary(key):
        values = [m[key] for m in per_fold if m[key] is not None]
        if not values:  # e.g. AUC when every validation fold holds one class only
            return {"mean": None, "sd": None}
        return {"mean": round(statistics.mean(values), 4),
                "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0}

    run_id = new_run_id()
    atlas = short_atlas_name(args.atlas)
    oof_file = oof_path(atlas, run_id)
    oof_sha = write_oof(pd.concat(oof_parts, ignore_index=True), oof_file, folds, frozen)
    metrics = {"cv_accuracy": summary("accuracy"),
               "cv_balanced_accuracy": summary("balanced_accuracy"),
               "cv_auc": summary("auc"),
               "cv_majority_baseline": summary("majority_baseline"),
               "chosen_epochs": int(statistics.median(m["best_epoch"] for m in per_fold)),
               "per_fold": per_fold,
               "oof": {"file": oof_file.as_posix(), "sha256": oof_sha, "n": len(folds)},
               "cv_seconds": round(time.perf_counter() - started, 1)}
    log_run({"run_id": run_id, "stage": "cv", "dataset": DATASET,
             "atlas": atlas, "seed": args.seed,
             "hyperparameters": hyperparameters(args), "metrics": metrics,
             "data_config": data_config(args, cset),
             "split_sizes": {"development_pool": len(folds), "folds": len(per_fold)},
             "checkpoint_path": "none (cross-validation)", "git_commit": code_version()})
    print(f"\nCV accuracy {metrics['cv_accuracy']} vs majority baseline "
          f"{metrics['cv_majority_baseline']} | balanced {metrics['cv_balanced_accuracy']}")
    print(f"Chosen number of epochs for the final model: {metrics['chosen_epochs']}")
    print(f"Out-of-fold probabilities: {oof_file} ({len(folds)} participants)")
    print(f"Cross-validation time: {metrics['cv_seconds']} s")
    print(f"Run logged. run_id = {run_id}")
    print(f"Next: python scripts/train_gnn.py --stage final --epochs-from-cv {run_id}")


def previous_frozen_runs(atlas: str) -> list[dict]:
    return [r for r in read_runs() if r.get("dataset") == DATASET and r.get("atlas") == atlas
            and r.get("stage") == "final"]


def stage_final(args, cset, folds, frozen, device):
    atlas = short_atlas_name(args.atlas)
    earlier = previous_frozen_runs(atlas)
    if earlier and not args.allow_repeat:
        raise SystemExit(
            f"The frozen set was already measured for {atlas} "
            f"(run {earlier[-1]['run_id']}). It is measured once. Use --allow-repeat only "
            "with a written reason; the repeat is recorded in the run log."
        )
    cv_run = get_run(args.epochs_from_cv) if args.epochs_from_cv else None
    if cv_run is None or cv_run.get("stage") != "cv" or cv_run.get("atlas") != atlas:
        raise SystemExit("--epochs-from-cv must be the run_id of a cross-validation run "
                         "for this atlas (it decides the number of epochs).")
    for key in ("hidden", "layers", "dropout", "lr", "batch_size"):
        setattr(args, key, cv_run["hyperparameters"][key])
    # runs logged before memo 0011 have no flag: they were unweighted
    args.class_weighted = bool(cv_run["hyperparameters"].get("class_weighted", False))
    args.tuning_grid = None  # the tag marks tuning (CV) runs only
    args.density = cv_run["data_config"]["density"]
    args.fill_nan = cv_run["data_config"]["fill_nan"]
    args.epochs = cv_run["metrics"]["chosen_epochs"]

    print(f"\n== Final model: whole development pool, {args.epochs} epochs "
          f"(from CV run {cv_run['run_id']}) ==")
    train = build_graphs(cset, folds, args.density, args.fill_nan)
    model, _ = fit(train, None, args, device)

    run_id = new_run_id()
    ckpt_path = Path("checkpoints") / f"{atlas}_{run_id}.pt"
    ckpt_path.parent.mkdir(exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "in_dim": cset.n_regions, "num_classes": 2,
                "hidden": args.hidden, "layers": args.layers, "dropout": args.dropout,
                "atlas": atlas, "atlas_key": args.atlas, "density": args.density,
                "fill_nan": args.fill_nan, "run_id": run_id}, ckpt_path)

    # ---- ONE measurement on the frozen set
    print("\n== Frozen evaluation set: measured once ==")
    frozen_graphs = build_graphs(cset, frozen, args.density, args.fill_nan)
    reloaded = model_from_checkpoint(torch.load(ckpt_path, map_location="cpu")).to(device)
    frozen_metrics, logits_a = scores(reloaded, frozen_graphs, device, args.batch_size)
    again = model_from_checkpoint(torch.load(ckpt_path, map_location="cpu")).to(device)
    _, logits_b = scores(again, frozen_graphs, device, args.batch_size)
    identical = bool(torch.allclose(logits_a, logits_b, atol=1e-6))
    # the same single measurement, kept per participant for calibration (memo 0010)
    pred_file = frozen_predictions_path(atlas, run_id)
    pred_sha = write_frozen_predictions(
        fold_rows(frozen, -1, [int(g.y) for g in frozen_graphs],
                  torch.softmax(logits_a, dim=1)[:, 1].numpy()).drop(columns="fold"),
        pred_file, frozen, folds)
    frozen_metrics["predictions"] = {"file": pred_file.as_posix(), "sha256": pred_sha,
                                     "n": len(frozen_graphs)}

    log_run({"run_id": run_id, "stage": "final", "dataset": DATASET, "atlas": atlas,
             "seed": args.seed, "hyperparameters": hyperparameters(args),
             "metrics": {"frozen": frozen_metrics, "cv_run_id": cv_run["run_id"],
                         "cv_accuracy": cv_run["metrics"]["cv_accuracy"]},
             "data_config": data_config(args, cset),
             "split_sizes": {"train": len(train), "frozen": len(frozen_graphs)},
             "checkpoint_path": str(ckpt_path), "reload_identical": identical,
             "repeat_frozen_measurement": bool(earlier), "git_commit": code_version()})
    register_model(run_id)
    print(f"Frozen set: {frozen_metrics}")
    print(f"Majority-class baseline on the frozen set: {frozen_metrics['majority_baseline']}")
    print(f"Reload reproduces identical predictions: {identical}")
    print(f"Run logged and registered for atlas '{atlas}'. run_id = {run_id}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stage", choices=["cv", "final"], required=True)
    p.add_argument("--atlas", default="rois_cc200")
    p.add_argument("--connectomes", default="data/processed/connectomes")
    p.add_argument("--density", type=float, default=0.10)
    p.add_argument("--fill-nan", dest="fill_nan", type=float, default=0.0)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--layers", type=int, default=3)
    p.add_argument("--dropout", type=float, default=0.5)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch-size", dest="batch_size", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs-from-cv", dest="epochs_from_cv")
    p.add_argument("--allow-repeat", dest="allow_repeat", action="store_true")
    p.add_argument("--class-weighted", dest="class_weighted", action="store_true",
                   help="weight the loss by class, from each training fold (memo 0011)")
    p.add_argument("--tuning-grid", dest="tuning_grid",
                   help="tag a CV run as part of a declared tuning grid, e.g. 0011-v1")
    args = p.parse_args()
    if args.tuning_grid and args.stage != "cv":
        p.error("--tuning-grid tags cross-validation runs only")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)
    folds = read_ids(FOLDS_FILE)
    frozen = read_ids(FROZEN_FILE)
    assert_no_leakage(folds, frozen, context=str(FOLDS_FILE))  # before any training
    print(f"Leakage check passed: {len(folds)} development, {len(frozen)} frozen, no overlap.")
    cset = load_connectomes(args.connectomes, args.atlas)
    print(f"Atlas {args.atlas}: {cset.n_regions} regions, {len(cset)} participants")

    if args.stage == "cv":
        stage_cv(args, cset, folds, frozen, device)
    else:
        stage_final(args, cset, folds, frozen, device)


if __name__ == "__main__":
    main()
