"""Out-of-fold predictions from cross-validation, and frozen-set predictions (memo 0010).

In 5-fold cross-validation every development participant is in the validation fold
exactly once. The probability the fold's model gave that participant, while it was
held out, is its out-of-fold (OOF) prediction. Together they are one honest score per
development participant, from a model that never trained on them.

Calibration (memo 0010) is fitted on these, never on the frozen set (memo 0011,
section 4). So the file must cover the development pool exactly, once each, and hold
no frozen participant: `check_oof` enforces that before the file is written.

File: runs/oof/<atlas>_<cv run_id>_oof.csv, one row per participant, sorted by SUB_ID.
The cross-validation run's log entry records its path and SHA-256 under
metrics["oof"], so the file can be tied to the run that produced it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

OOF_DIR = Path("runs/oof")
COLUMNS = ("SUB_ID", "FILE_ID", "SITE_ID", "fold", "label", "prob_autism", "prediction")


def oof_path(atlas: str, run_id: str, folder: Path = OOF_DIR) -> Path:
    return Path(folder) / f"{atlas}_{run_id}_oof.csv"


def fold_rows(table: pd.DataFrame, fold: int, labels: np.ndarray,
              prob_autism: np.ndarray) -> pd.DataFrame:
    """The OOF rows of one validation fold, in the fold's own order.

    `table` holds that fold's rows of the split file (SUB_ID, FILE_ID, SITE_ID);
    `labels` and `prob_autism` are in the same order.
    """
    if not (len(table) == len(labels) == len(prob_autism)):
        raise ValueError("table, labels and probabilities must have the same length")
    prob = np.asarray(prob_autism, dtype=float)
    return pd.DataFrame({
        "SUB_ID": table["SUB_ID"].astype(int).to_numpy(),
        "FILE_ID": table["FILE_ID"].astype(str).to_numpy(),
        "SITE_ID": table["SITE_ID"].astype(str).to_numpy(),
        "fold": int(fold),
        "label": np.asarray(labels, dtype=int),
        "prob_autism": prob,
        "prediction": (prob >= 0.5).astype(int),
    })


def check_oof(oof: pd.DataFrame, development: pd.DataFrame,
              frozen: pd.DataFrame | None = None) -> None:
    """Raise ValueError unless `oof` is one valid row per development participant."""
    missing_cols = [c for c in COLUMNS if c not in oof.columns]
    if missing_cols:
        raise ValueError(f"OOF table is missing columns: {missing_cols}")
    ids = oof["SUB_ID"].astype(int)
    if ids.duplicated().any():
        dup = sorted(set(ids[ids.duplicated()]))[:10]
        raise ValueError(f"participants with more than one OOF prediction: {dup}")
    expected = set(development["SUB_ID"].astype(int))
    if set(ids) != expected:
        raise ValueError(
            f"OOF covers {len(set(ids))} participants but the development pool has "
            f"{len(expected)}: missing {sorted(expected - set(ids))[:10]}, "
            f"extra {sorted(set(ids) - expected)[:10]}"
        )
    if frozen is not None:
        leaked = set(ids) & set(frozen["SUB_ID"].astype(int))
        if leaked:
            raise ValueError(f"frozen participants in the OOF table: {sorted(leaked)[:10]}")
    prob = oof["prob_autism"].to_numpy(dtype=float)
    if not np.isfinite(prob).all() or (prob < 0).any() or (prob > 1).any():
        raise ValueError("prob_autism must be finite and between 0 and 1")
    if not set(oof["label"].astype(int)) <= {0, 1}:
        raise ValueError("label must be 0 (control) or 1 (autism)")


def write_oof(oof: pd.DataFrame, path: Path, development: pd.DataFrame,
              frozen: pd.DataFrame | None = None) -> str:
    """Check, then write the OOF table sorted by SUB_ID. Returns the file's SHA-256."""
    check_oof(oof, development, frozen)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = oof.loc[:, list(COLUMNS)].sort_values("SUB_ID").reset_index(drop=True)
    out.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_oof(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"FILE_ID": str, "SITE_ID": str})


# ---------------------------------------------------------------------------
# Frozen-set predictions (memo 0010): the one measurement, kept per participant
# ---------------------------------------------------------------------------

FROZEN_DIR = Path("runs/frozen_predictions")
FROZEN_COLUMNS = ("SUB_ID", "FILE_ID", "SITE_ID", "label", "prob_autism", "prediction")


def frozen_predictions_path(atlas: str, run_id: str, folder: Path = FROZEN_DIR) -> Path:
    return Path(folder) / f"{atlas}_{run_id}_frozen.csv"


def write_frozen_predictions(rows: pd.DataFrame, path: Path, frozen: pd.DataFrame,
                             development: pd.DataFrame) -> str:
    """Write the final model's frozen-set probabilities. Returns the file's SHA-256.

    Written by `train_gnn.py --stage final` from the same single measurement that gives
    the frozen accuracy, so keeping it is not a second look. It must cover the frozen
    set exactly and contain no development participant.
    """
    check_oof(rows.assign(fold=-1), frozen)
    leaked = set(rows["SUB_ID"].astype(int)) & set(development["SUB_ID"].astype(int))
    if leaked:
        raise ValueError(f"development participants in frozen predictions: {sorted(leaked)[:10]}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = rows.loc[:, list(FROZEN_COLUMNS)].sort_values("SUB_ID").reset_index(drop=True)
    out.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()
