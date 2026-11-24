"""The four-atlas ensemble, the project's final model (memo 0017).

For each participant: the equal-weight mean of the four final models' probability of
autism; autism when the mean is at least 0.5. Nothing is fitted, so the module only
reads saved predictions and never runs a model.

- `cv_evidence` scores the rule on the out-of-fold files of the selected CV runs (the
  evidence memo 0017 was written from; the frozen set is not touched).
- `load_frozen_members` reads the final runs' saved frozen-set predictions, hash checked,
  and refuses members that disagree on participants or labels.
- `frozen_ensemble` combines them once; `scripts/ensemble.py` records the result and
  refuses a second measurement.

The record goes to its own file, `runs/ensemble_log.jsonl`, not the run log: the run log
and its database table (memo 0008) hold training runs, and an ensemble trains nothing.
`neurographx.integrity` checks that file (section 8).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score

from neurographx.integrity import text_hash_matches
from neurographx.m3_model.run_logger import get_run, read_registry, read_runs

THRESHOLD = 0.5
ORDER = ("aal", "cc200", "ho", "dosenbach160")

# Declared in memo 0017, section 1: the registered final run of each atlas. The memo
# applies to these runs only; a different registry needs a new memo, not a silent swap.
MEMBERS = {"aal": "57900b0d", "cc200": "cf60f29e", "ho": "76533df4",
           "dosenbach160": "5ee28510"}


def combine(probs: np.ndarray) -> np.ndarray:
    """Mean probability of autism over members (columns), one row per participant."""
    probs = np.asarray(probs, dtype=float)
    if probs.ndim != 2 or probs.shape[1] == 0:
        raise ValueError("expected a participants x members array of probabilities")
    if np.isnan(probs).any() or (probs < 0).any() or (probs > 1).any():
        raise ValueError("probabilities must lie between 0 and 1, with no missing values")
    return probs.mean(axis=1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for a proportion k/n, as for the single models."""
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def scores(y, prob) -> dict:
    """The metrics the single final models record, plus the Wilson interval."""
    y = np.asarray(y, dtype=int)
    prob = np.asarray(prob, dtype=float)
    pred = (prob >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel().tolist()
    lo, hi = wilson(tn + tp, len(y))
    return {
        "n": int(len(y)),
        "accuracy": round(float(np.mean(pred == y)), 4),
        "accuracy_ci95_wilson": [round(lo, 4), round(hi, 4)],
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
        "auc": round(float(roc_auc_score(y, prob)), 4) if len(set(y)) == 2 else None,
        "majority_baseline": round(float(max(np.mean(y == 0), np.mean(y == 1))), 4),
        "confusion_tn_fp_fn_tp": [tn, fp, fn, tp],
        "predicted_autism": int(pred.sum()),
    }


def _merge(frames: dict[str, pd.DataFrame], extra: tuple[str, ...] = ()) -> pd.DataFrame:
    """One row per participant with every member's probability; refuses any mismatch."""
    atlases = list(frames)
    first = frames[atlases[0]].set_index("SUB_ID").sort_index()
    for atlas in atlases:
        df = frames[atlas].set_index("SUB_ID").sort_index()
        if df.index.duplicated().any():
            raise ValueError(f"{atlas}: a participant appears more than once")
        if not df.index.equals(first.index):
            raise ValueError(f"{atlas}: its participants differ from {atlases[0]}'s")
        if not df["label"].equals(first["label"]):
            raise ValueError(f"{atlas}: its labels differ from {atlases[0]}'s")
    out = first.loc[:, ["label", *extra]].copy()
    for atlas in atlases:
        out[f"prob_{atlas}"] = frames[atlas].set_index("SUB_ID").sort_index()["prob_autism"]
    return out


# ---------------------------------------------------------------------------
# Cross-validation evidence (memo 0017, section 2)
# ---------------------------------------------------------------------------

def cv_evidence(root: Path, members: dict[str, str] = MEMBERS,
                log_path: Path | None = None) -> dict:
    """Fold mean and SD of each member and of the ensemble, on out-of-fold predictions."""
    root = Path(root)
    runs = {r["run_id"]: r for r in read_runs(log_path or root / "runs/run_log.jsonl")}
    frames = {}
    for atlas, final_id in members.items():
        cv_id = runs[final_id]["metrics"]["cv_run_id"]
        meta = runs[cv_id]["metrics"]["oof"]
        path = root / meta["file"]
        if not text_hash_matches(path, meta["sha256"]):
            raise ValueError(f"{atlas}: {meta['file']} differs from the hash in run {cv_id}")
        frames[atlas] = pd.read_csv(path)
    table = _merge(frames, extra=("fold",))
    table["prob_ensemble"] = combine(table[[f"prob_{a}" for a in members]].to_numpy())

    def per_fold(col):
        rows = []
        for _, g in table.groupby("fold"):
            y, p = g["label"].to_numpy(), g[col].to_numpy()
            pred = (p >= THRESHOLD).astype(int)
            rows.append({"accuracy": np.mean(pred == y),
                         "balanced_accuracy": balanced_accuracy_score(y, pred),
                         "auc": roc_auc_score(y, p)})
        out = {}
        for key in ("accuracy", "balanced_accuracy", "auc"):
            vals = np.array([r[key] for r in rows], dtype=float)
            out[key] = {"mean": round(float(vals.mean()), 4),
                        "sd": round(float(vals.std(ddof=1)), 4)}
        return out

    result = {a: per_fold(f"prob_{a}") for a in members}
    result["ensemble"] = per_fold("prob_ensemble")
    result["n"] = int(len(table))
    return result


# ---------------------------------------------------------------------------
# The single frozen-set evaluation (memo 0017, section 4)
# ---------------------------------------------------------------------------

def check_members(registry: dict, members: dict[str, str] = MEMBERS) -> None:
    """The registry must serve exactly the runs memo 0017 names."""
    served = {a: e["run_id"] for a, e in registry.items()}
    if served != members:
        raise ValueError(f"the registry serves {served}, but memo 0017 names {members}; "
                         "a different set of models needs a new memo")


def load_frozen_members(root: Path, members: dict[str, str] = MEMBERS,
                        log_path: Path | None = None) -> pd.DataFrame:
    """Each member's saved frozen predictions, hash checked against the run log."""
    root = Path(root)
    log_path = log_path or root / "runs/run_log.jsonl"
    frames = {}
    for atlas, run_id in members.items():
        run = get_run(run_id, log_path)
        if run is None or run.get("stage") != "final":
            raise ValueError(f"{atlas}: run {run_id} is not a final run in the run log")
        meta = run["metrics"]["frozen"]["predictions"]
        path = root / meta["file"]
        if not path.exists():
            raise ValueError(f"{atlas}: {meta['file']} not found")
        if not text_hash_matches(path, meta["sha256"]):
            raise ValueError(f"{atlas}: {meta['file']} differs from the hash in run {run_id}")
        frames[atlas] = pd.read_csv(path)
    return _merge(frames, extra=("FILE_ID", "SITE_ID"))


REQUIRED = ("ensemble_id", "timestamp", "dataset", "members", "rule", "metrics",
            "predictions")


def read_ensemble_log(path: Path) -> list[dict]:
    """Every record of `runs/ensemble_log.jsonl`; empty when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def append_ensemble_record(path: Path, record: dict) -> None:
    missing = [k for k in REQUIRED if k not in record]
    if missing:
        raise ValueError(f"ensemble record is missing {missing}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def previous_measurements(ensemble_log_path: Path, dataset: str) -> list[dict]:
    return [r for r in read_ensemble_log(ensemble_log_path) if r.get("dataset") == dataset]


def frozen_ensemble(members_table: pd.DataFrame, atlases: tuple[str, ...]) -> tuple[dict,
                                                                                     pd.DataFrame]:
    """Metrics and per-participant predictions of the ensemble on the frozen set."""
    table = members_table.copy()
    prob = combine(table[[f"prob_{a}" for a in atlases]].to_numpy())
    metrics = scores(table["label"], prob)  # from the unrounded mean
    table["prob_autism"] = prob.round(6)
    table["prediction"] = (prob >= THRESHOLD).astype(int)
    return metrics, table.reset_index()


def registry_members(registry_path: Path) -> dict[str, str]:
    registry = read_registry(registry_path)
    return {a: registry[a]["run_id"] for a in ORDER if a in registry}
