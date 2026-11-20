"""Train and evaluation splits for one reliability job (memo 0016).

Every split is drawn from the development pool (the participants in the CV folds file).
The frozen evaluation set is never used: the runner checks that the pool and the frozen
set share no participant before any split is made.

    atlas, seed   the five CV folds of the folds file, unchanged, so only the atlas or
                  the training seed differs between jobs
    resample      one stratified bootstrap of the pool (drawn with replacement, the same
                  number of participants per diagnosis as the pool), evaluated on the
                  participants the bootstrap did not draw ("out of bag")
    site          every other site trains, the named site is evaluated
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from neurographx.m5_reliability.manifest import Job

NEEDED_COLUMNS = ("SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP", "fold")


class SplitError(ValueError):
    """A job cannot be split on this development pool."""


@dataclass(frozen=True)
class Split:
    name: str                 # "fold 0", "bootstrap 1", "site SYN_A"
    train: pd.DataFrame
    evaluate: pd.DataFrame


def check_pool(pool: pd.DataFrame) -> None:
    missing = [c for c in NEEDED_COLUMNS if c not in pool.columns]
    if missing:
        raise SplitError(f"the development pool lacks columns {missing}")
    if pool["SUB_ID"].duplicated().any():
        raise SplitError("the development pool lists a participant twice")


def bootstrap(pool: pd.DataFrame, seed: int, index: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A stratified bootstrap and its out-of-bag rows. Same seed and index, same draw."""
    rng = np.random.default_rng([int(seed), int(index)])
    drawn = []
    for _, group in pool.groupby("DX_GROUP", sort=True):
        positions = rng.integers(0, len(group), size=len(group))
        drawn.append(group.iloc[positions])
    train = pd.concat(drawn, ignore_index=True)
    out_of_bag = pool[~pool["SUB_ID"].isin(train["SUB_ID"])].reset_index(drop=True)
    return train, out_of_bag


def splits_for(job: Job, pool: pd.DataFrame) -> list[Split]:
    check_pool(pool)
    if job.axis in ("atlas", "seed"):
        return [Split(f"fold {k}", pool[pool["fold"] != k].reset_index(drop=True),
                      pool[pool["fold"] == k].reset_index(drop=True))
                for k in sorted(pool["fold"].unique())]
    if job.axis == "resample":
        train, out_of_bag = bootstrap(pool, job.seed, int(job.value))
        if out_of_bag.empty:
            raise SplitError(f"bootstrap {job.value} drew every participant; nothing is "
                             "left out to evaluate on")
        return [Split(f"bootstrap {job.value}", train, out_of_bag)]
    if job.axis == "site":
        held = pool["SITE_ID"].astype(str) == str(job.value)
        if not held.any():
            raise SplitError(f"site {job.value} has no participant in the development pool")
        train = pool[~held].reset_index(drop=True)
        if train["DX_GROUP"].nunique() < 2:
            raise SplitError(f"without site {job.value} the training set holds one "
                             "diagnosis only")
        return [Split(f"site {job.value}", train, pool[held].reset_index(drop=True))]
    raise SplitError(f"unknown axis {job.axis!r}")
