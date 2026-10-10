"""Frozen evaluation set, development folds, and the leakage guard.

Vocabulary used across the project:

- **QC cohort**: every participant who passed quality control (memo 0003).
- **Frozen evaluation set**: 100 participants drawn once from the QC cohort,
  stratified by site and diagnostic group together, never regenerated (memo 0005).
  No model ever trains on them, tunes on them, or selects a checkpoint with them.
- **Development pool**: QC cohort minus the frozen set. All training,
  validation and cross-validation splits come from here.
- **Leakage**: any frozen participant appearing in a training split.

Stratified draw, in plain terms: participants are grouped into cells, one per
(site, diagnostic group) pair. Each cell receives a share of the 100 places in
proportion to its size, rounded with the largest remainder method so the shares
add up to exactly 100. Within each cell, that many participants are chosen at
random with a fixed seed. The result mirrors the cohort's mix of sites and
groups, so no single hospital or group dominates the evaluation.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

KEY_COLUMNS = ["SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP"]


class LeakageError(AssertionError):
    """Raised when a frozen evaluation participant appears in a training split."""


# ---------------------------------------------------------------------------
# Allocation and the stratified draw
# ---------------------------------------------------------------------------

def allocate(counts: pd.Series, total: int) -> pd.Series:
    """Proportional allocation with the largest remainder method.

    `counts` is indexed by stratum and holds the stratum sizes. Returns how many
    to draw from each stratum. The result sums to `total`, never exceeds a
    stratum's size, and is deterministic: ties in the remainder are broken by
    the sorted stratum key.
    """
    counts = counts.sort_index()
    n = int(counts.sum())
    if not 0 < total <= n:
        raise ValueError(f"Cannot draw {total} from {n} participants")
    exact = counts * total / n
    alloc = np.floor(exact).astype(int)
    remainder = (exact - alloc).to_frame("rem")
    remainder["order"] = range(len(remainder))
    remainder = remainder[alloc < counts]
    short = total - int(alloc.sum())
    winners = remainder.sort_values(["rem", "order"], ascending=[False, True]).index[:short]
    alloc.loc[winners] += 1
    return alloc.astype(int)


def stratified_draw(cohort: pd.DataFrame, size: int, strata: list[str],
                    seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Draw `size` participants stratified by `strata`. Returns (drawn, allocation table)."""
    if cohort["SUB_ID"].duplicated().any():
        raise ValueError("Duplicate SUB_ID in the cohort")
    ordered = cohort.sort_values("SUB_ID").reset_index(drop=True)
    groups = ordered.groupby(strata, sort=True)
    counts = groups.size()
    alloc = allocate(counts, size)

    rng = np.random.default_rng(seed)
    picked = []
    for key, members in groups:            # sorted order, so the rng stream is reproducible
        k = int(alloc.loc[key])
        if k:
            rows = rng.choice(len(members), size=k, replace=False)
            picked.append(members.iloc[np.sort(rows)])
    drawn = pd.concat(picked).sort_values("SUB_ID").reset_index(drop=True)

    table = counts.rename("in_cohort").to_frame()
    table["drawn"] = alloc
    table["expected"] = (counts * size / counts.sum()).round(2)
    return drawn, table.reset_index()


def make_folds(pool: pd.DataFrame, k: int, strata: list[str], seed: int) -> pd.DataFrame:
    """Stratified k-fold assignment over the development pool.

    Within each stratum the members are shuffled with the seed and dealt to the
    folds in turn, starting each stratum at the next fold so small strata do not
    all land in fold 0. Every participant gets exactly one fold in 0..k-1.
    """
    ordered = pool.sort_values("SUB_ID").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    fold = np.empty(len(ordered), dtype=int)
    start = 0
    for _, members in ordered.groupby(strata, sort=True):
        idx = members.index.to_numpy()[rng.permutation(len(members))]
        fold[idx] = (np.arange(len(idx)) + start) % k
        start = (start + len(idx)) % k
    out = ordered[KEY_COLUMNS].copy()
    out["fold"] = fold
    return out


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def sha256_text(path: Path) -> str:
    """Hash of a text file with line endings normalised, so Windows checkouts still match."""
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def write_frozen(drawn: pd.DataFrame, table: pd.DataFrame, csv_path: Path, meta_path: Path,
                 cohort_path: Path, seed: int, strata: list[str]) -> dict:
    """Write the frozen set and its sidecar. Refuses to overwrite an existing set."""
    if csv_path.exists():
        raise FileExistsError(f"{csv_path} already exists. The frozen set is never regenerated.")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    drawn[KEY_COLUMNS].to_csv(csv_path, index=False, lineterminator="\n")
    meta = {
        "description": "Frozen evaluation set. Drawn once, never regenerated. See memo 0005.",
        "drawn_on": dt.date.today().isoformat(),
        "size": int(len(drawn)),
        "seed": int(seed),
        "stratify_by": strata,
        "method": "proportional allocation, largest remainder, numpy default_rng choice "
                  "without replacement within each stratum, strata in sorted order, "
                  "cohort sorted by SUB_ID",
        "numpy_version": np.__version__,
        "cohort_file": str(cohort_path.name),
        "cohort_size": None,
        "cohort_sha256": sha256_text(cohort_path),
        "frozen_sha256": sha256_text(csv_path),
        "allocation": table.to_dict(orient="records"),
    }
    meta["cohort_size"] = int(table["in_cohort"].sum())
    meta_path.write_text(json.dumps(meta, indent=2, default=int) + "\n", encoding="utf-8")
    return meta


def read_ids(path: Path) -> pd.DataFrame:
    """Read any split or frozen file. Needs SUB_ID; FILE_ID is checked when present."""
    df = pd.read_csv(path)
    if "SUB_ID" not in df.columns:
        raise ValueError(f"{path} has no SUB_ID column")
    return df


# ---------------------------------------------------------------------------
# The leakage guard
# ---------------------------------------------------------------------------

def find_leaks(training: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    """Rows of `training` whose SUB_ID or FILE_ID belongs to the frozen set."""
    hit = training["SUB_ID"].astype(np.int64).isin(frozen["SUB_ID"].astype(np.int64))
    if "FILE_ID" in training.columns and "FILE_ID" in frozen.columns:
        hit |= training["FILE_ID"].astype(str).isin(frozen["FILE_ID"].astype(str))
    return training[hit]


def assert_no_leakage(training: pd.DataFrame | Iterable[int], frozen: pd.DataFrame,
                      context: str = "training split") -> None:
    """Raise LeakageError if any frozen participant is in `training`.

    `training` is a frame with SUB_ID (and optionally FILE_ID), or an iterable of
    SUB_IDs. Training code calls this before fitting; the pytest suite calls it on
    every committed split file.
    """
    if not isinstance(training, pd.DataFrame):
        training = pd.DataFrame({"SUB_ID": list(training)})
    leaks = find_leaks(training, frozen)
    if len(leaks):
        ids = sorted(set(leaks["SUB_ID"].astype(int)))
        raise LeakageError(
            f"{len(ids)} frozen evaluation participant(s) found in {context}: {ids[:10]}"
            + (" ..." if len(ids) > 10 else "")
        )


def training_rows(split: pd.DataFrame) -> pd.DataFrame:
    """The rows of a split file that a model may train on.

    Conventions for files under data/splits/:
    - a `role` column: rows with role 'train' or 'val' are training rows;
    - a `fold` column (cross-validation): every row is a training row at some point;
    - neither: the whole file is treated as training rows.
    The conservative default means a new split format is checked, not skipped.
    """
    if "role" in split.columns:
        return split[split["role"].astype(str).str.lower().isin(["train", "val", "valid",
                                                                  "validation"])]
    return split
