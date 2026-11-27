"""Resumable runner for a reliability grid (memo 0016).

For each job of a manifest that the run log does not hold yet, the runner trains the
baseline GCN on each of the job's training splits, scores the matching evaluation split,
writes the per-participant probabilities to a CSV file, and appends one record to the
run log with ``"stage": "variant"``. A record is written only after its job has finished,
so a run that stops part way loses at most the job in progress; the same command again
skips every job already logged and continues with the rest.

Rules the runner enforces, in this order, before it trains anything:

1. Real ABIDE data is refused unless ``allow_real_data`` is set. The reliability finding
   is an FYP-II deliverable (memo 0015), so FYP-I runs the engine on the synthetic
   fixture only.
2. The fixture data itself is never written to: its files are hash-checked (memo 0014),
   so the output folder must lie outside ``fixtures/``.
3. The development pool and the frozen evaluation set share no participant. Only the
   pool is read for training or evaluation; the frozen set is read for its identifiers
   only, to make this check.

Every variant trains for exactly the configured number of epochs. No epoch is chosen on
the participants a variant is scored on, so the score is not tuned to them.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score

from neurographx import datasource
from neurographx.m1_ingestion.splits import assert_no_leakage, read_ids
from neurographx.m2_connectome.engine import sha256_file
from neurographx.m3_model.data import build_graphs, load_connectomes, short_atlas_name
from neurographx.m3_model.run_logger import log_run, new_run_id, read_runs
from neurographx.m5_reliability.manifest import (
    Job,
    expand,
    grid_dir,
    jobs_of,
    load_spec,
    manifest_path,
    write_manifest,
)
from neurographx.m5_reliability.variants import splits_for

STAGE = "variant"
CHECKPOINT_NOTE = "none (reliability variant)"
FIXTURE_DATASET = "synthetic_fixture"
REAL_DATASET = "ABIDE"

# A trainer takes (train graphs, evaluation graphs, settings, seed) and returns the
# probability of autism for each evaluation graph, in order.
Trainer = Callable[[list, list, dict, int], np.ndarray]


class RealDataRefused(RuntimeError):
    """Real ABIDE data was requested without allow_real_data."""


class OutputRefused(RuntimeError):
    """The output folder would write into the hash-checked fixture dataset."""


@dataclass
class Summary:
    manifest_id: str
    manifest_file: Path
    total: int
    done_before: int
    ran: list[str] = field(default_factory=list)       # run_ids written by this call
    remaining: int = 0


# ---------------------------------------------------------------------------
# Training and scoring
# ---------------------------------------------------------------------------

def gcn_trainer(train_graphs: list, eval_graphs: list, settings: dict, seed: int,
                device=None) -> np.ndarray:
    """The baseline GCN (memo 0006), trained for a fixed number of epochs."""
    import torch
    from torch_geometric.loader import DataLoader

    from neurographx.m3_model.model import GCN
    from neurographx.m3_model.training import class_weights, evaluate, set_seed, train_epoch

    device = device or torch.device("cpu")
    set_seed(seed)
    model = GCN(train_graphs[0].x.shape[1], settings["hidden"], 2, settings["layers"],
                settings["dropout"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings["lr"])
    weight = (class_weights([int(g.y) for g in train_graphs])
              if settings["class_weighted"] else None)
    loader = DataLoader(train_graphs, batch_size=settings["batch_size"], shuffle=True)
    for _ in range(settings["epochs"]):
        train_epoch(model, loader, optimizer, device, weight)
    _, logits = evaluate(model, DataLoader(eval_graphs, batch_size=settings["batch_size"]),
                         device)
    return torch.softmax(logits, dim=1)[:, 1].numpy()


def score(labels, prob_autism) -> dict:
    """Accuracy, balanced accuracy, AUC (None if one class only) and majority baseline."""
    y = np.asarray(labels, dtype=int)
    p = np.asarray(prob_autism, dtype=float)
    pred = (p > 0.5).astype(int)
    two_classes = len(set(y.tolist())) == 2
    return {
        "n": int(len(y)),
        "accuracy": round(float(np.mean(pred == y)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4)
        if two_classes else None,
        "auc": round(float(roc_auc_score(y, p)), 4) if two_classes else None,
        "majority_baseline": round(float(max(np.mean(y == 0), np.mean(y == 1))), 4),
        "confusion_tn_fp_fn_tp": confusion_matrix(y, pred, labels=[0, 1]).ravel().tolist(),
    }


def _sha256_frame(df: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = df.to_csv(index=False, lineterminator="\n")
    path.write_text(text, encoding="utf-8", newline="\n")  # the hash is of these LF bytes
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The grid
# ---------------------------------------------------------------------------

def done_job_ids(log_path: Path, manifest_id: str) -> set[str]:
    """Job identifiers of this manifest that the run log already holds."""
    done = set()
    for record in read_runs(log_path):
        rel = record.get("reliability") or {}
        if record.get("stage") == STAGE and rel.get("manifest_id") == manifest_id:
            done.add(rel.get("job_id"))
    return done


def pending(jobs: list[Job], log_path: Path, manifest_id: str) -> list[Job]:
    done = done_job_ids(log_path, manifest_id)
    return [j for j in jobs if j.job_id not in done]


def _check_output(out_dir: Path) -> None:
    fixtures = datasource.data_root("fixtures").resolve()
    out = Path(out_dir).resolve()
    if out == fixtures or fixtures in out.parents:
        raise OutputRefused(
            f"{out_dir} is inside the fixture dataset, whose files are hash-checked "
            "(memo 0014). Choose an output folder outside fixtures/.")


def _load_pool(root: Path, mode: str) -> tuple[pd.DataFrame, Path, Path]:
    folds_file, frozen_file = datasource.cv_folds(root), datasource.frozen_set(root)
    pool, frozen = read_ids(folds_file), read_ids(frozen_file)
    assert_no_leakage(pool, frozen, context=str(folds_file))
    if mode == "fixtures" and not pool["SITE_ID"].astype(str).str.startswith("SYN_").all():
        raise RealDataRefused(f"{folds_file} is not the synthetic fixture pool")
    return pool, folds_file, frozen_file


def run_job(job: Job, manifest: dict, pool: pd.DataFrame, root: Path, out_dir: Path,
            files: tuple[Path, Path], dataset: str, trainer: Trainer,
            connectome_cache: dict) -> str:
    """Run one job and log it. Returns the new run_id."""
    started = time.perf_counter()
    settings = manifest["spec"]["settings"]
    if job.atlas not in connectome_cache:
        connectome_cache[job.atlas] = load_connectomes(datasource.connectome_dir(root),
                                                       job.atlas)
    cset = connectome_cache[job.atlas]
    density, fill_nan = settings["density"], settings["fill_nan"]

    per_split, rows = [], []
    for split in splits_for(job, pool):
        train = build_graphs(cset, split.train, density, fill_nan)
        evaluate = build_graphs(cset, split.evaluate, density, fill_nan)
        labels = [int(g.y) for g in evaluate]
        prob = np.asarray(trainer(train, evaluate, settings, job.seed), dtype=float)
        if prob.shape != (len(evaluate),):
            raise ValueError(f"the trainer returned {prob.shape} probabilities for "
                             f"{len(evaluate)} participants")
        per_split.append({"split": split.name, "n_train": len(train), **score(labels, prob)})
        rows.append(split.evaluate[["SUB_ID", "FILE_ID", "SITE_ID"]].assign(
            split=split.name, label=labels, prob_autism=np.round(prob, 6)))

    predictions = pd.concat(rows, ignore_index=True)
    pred_rel = grid_dir(Path("."), manifest["name"]) / f"{job.job_id}.csv"
    pred_sha = _sha256_frame(predictions, Path(out_dir) / pred_rel)
    folds_file, frozen_file = files
    run_id = new_run_id()
    log_run({
        "run_id": run_id,
        "stage": STAGE,
        "dataset": dataset,
        "atlas": short_atlas_name(job.atlas),
        "seed": job.seed,
        "hyperparameters": {k: settings[k] for k in ("hidden", "layers", "dropout", "lr",
                                                     "batch_size", "epochs",
                                                     "class_weighted")},
        "metrics": {
            "pooled": score(predictions["label"], predictions["prob_autism"]),
            "per_split": per_split,
            "predictions": {"file": pred_rel.as_posix(), "sha256": pred_sha,
                            "n": len(predictions)},
            "seconds": round(time.perf_counter() - started, 1),
        },
        "data_config": {
            "atlas_key": job.atlas, "density": density, "fill_nan": fill_nan,
            "folds_file": folds_file.relative_to(root).as_posix(),
            "folds_sha256": sha256_file(folds_file),
            "frozen_file": frozen_file.relative_to(root).as_posix(),
            "frozen_sha256": sha256_file(frozen_file),
            "connectome_engine": cset.manifest.get("engine_version"),
            "connectome_sha256": cset.manifest.get("output_sha256"),
        },
        "split_sizes": {"development_pool": len(pool), "splits": len(per_split),
                        "evaluated": len(predictions)},
        "checkpoint_path": CHECKPOINT_NOTE,
        "reliability": {"grid": manifest["name"], "manifest_id": manifest["manifest_id"],
                        "job_id": job.job_id, "axis": job.axis, "value": job.value},
    }, Path(out_dir) / datasource.RUN_LOG)
    return run_id


def run_grid(spec_path: Path, out_dir: Path, mode: str = "fixtures", *,
             allow_real_data: bool = False, data_root: Path | None = None,
             max_jobs: int | None = None, dry_run: bool = False,
             trainer: Trainer = gcn_trainer, echo: Callable[[str], None] = print) -> Summary:
    """Expand the grid, write its manifest once, and run the jobs not yet logged.

    `data_root` overrides the folder for `mode` (tests use a copy of the fixture).
    """
    if mode not in datasource.MODES:
        raise ValueError(f"mode must be one of {datasource.MODES}")
    if mode == "real" and not allow_real_data:
        raise RealDataRefused(
            "Reliability runs on real ABIDE data are an FYP-II deliverable (memos 0015, "
            "0016). Run on the fixture, or give --allow-real-data (allow_real_data=True) "
            "when that work starts.")
    root = Path(data_root) if data_root else datasource.data_root(mode)
    out_dir = Path(out_dir)
    _check_output(out_dir)
    pool, folds_file, frozen_file = _load_pool(root, mode)
    manifest = expand(load_spec(spec_path), sorted(pool["SITE_ID"].astype(str).unique()))
    jobs = jobs_of(manifest)
    log_path = out_dir / datasource.RUN_LOG
    todo = pending(jobs, log_path, manifest["manifest_id"])
    summary = Summary(manifest["manifest_id"], manifest_path(out_dir, manifest["name"]),
                      len(jobs), len(jobs) - len(todo), remaining=len(todo))
    echo(f"Grid {manifest['name']} (manifest {manifest['manifest_id']}): {len(jobs)} jobs, "
         f"{summary.done_before} already logged, {len(todo)} to run.")
    if dry_run:
        for i, job in enumerate(todo, 1):
            echo(f"  [{i}/{len(todo)}] {job.label()}")
        echo("Dry run: nothing trained, nothing written.")
        return summary
    write_manifest(manifest, out_dir)
    dataset = FIXTURE_DATASET if mode == "fixtures" else REAL_DATASET
    cache: dict = {}
    for i, job in enumerate(todo[:max_jobs] if max_jobs is not None else todo, 1):
        run_id = run_job(job, manifest, pool, root, out_dir, (folds_file, frozen_file),
                         dataset, trainer, cache)
        summary.ran.append(run_id)
        summary.remaining -= 1
        echo(f"  [{i}/{len(todo)}] {job.label()}: logged as run {run_id}")
    echo(f"{summary.total - summary.remaining} of {summary.total} jobs logged; "
         f"{summary.remaining} remaining.")
    return summary
