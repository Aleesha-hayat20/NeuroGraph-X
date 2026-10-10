"""Independent recomputation of stored connectomes.

The engine reads .1D files with numpy.loadtxt, correlates with numpy.corrcoef
and transforms with numpy.arctanh. Everything here deliberately takes a
different route, so that a shared bug cannot make both sides agree:

- reading:      pandas.read_csv, whitespace separated, '#' header skipped
- correlation:  (a) the textbook formula written out by hand: centre each region,
                    divide by its norm, take dot products;
                (b) scipy.stats.pearsonr on a random sample of region pairs;
                (c) nilearn ConnectivityMeasure with the plain empirical covariance
                    (its default is Ledoit-Wolf shrinkage, which is NOT Pearson r)
- Fisher z:     0.5 * ln((1 + r) / (1 - r)) written out, not arctanh
- NaN pattern:  must sit exactly on the zero-variance regions found independently

Tolerances reflect float32 storage: about 7 significant digits.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

R_ATOL = 1e-6        # float32 rounding of values in [-1, 1] is below 6e-8
Z_RTOL = 1e-5        # z grows without bound near |r| = 1, so compare relatively
Z_ATOL = 1e-5


def read_1d_independent(path: Path) -> np.ndarray:
    df = pd.read_csv(path, sep=r"\s+", comment="#", header=None, engine="python")
    return df.to_numpy(dtype=np.float64)


def manual_pearson(ts: np.ndarray) -> np.ndarray:
    """r_ij = sum((x_i - mean_i)(x_j - mean_j)) / (||x_i - mean_i|| * ||x_j - mean_j||)."""
    centred = ts - ts.mean(axis=0, keepdims=True)
    norms = np.sqrt((centred ** 2).sum(axis=0))
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = centred / norms
        r = unit.T @ unit
    flat = norms < 1e-10 * np.sqrt(ts.shape[0])
    r[flat, :] = np.nan
    r[:, flat] = np.nan
    return r


def manual_fisher(r: np.ndarray, clip: float) -> np.ndarray:
    rc = np.clip(r, -clip, clip)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = 0.5 * np.log((1.0 + rc) / (1.0 - rc))
    np.fill_diagonal(z, 0.0)
    return z


def nilearn_pearson(ts: np.ndarray, keep: np.ndarray) -> np.ndarray:
    """nilearn correlation on the non-flat regions only."""
    from nilearn.connectome import ConnectivityMeasure
    from sklearn.covariance import EmpiricalCovariance

    measure = ConnectivityMeasure(cov_estimator=EmpiricalCovariance(), kind="correlation",
                                  standardize=False)
    return measure.fit_transform([ts[:, keep]])[0]


def scipy_pairs(ts: np.ndarray, pairs: np.ndarray) -> np.ndarray:
    from scipy.stats import pearsonr

    return np.array([pearsonr(ts[:, i], ts[:, j]).statistic for i, j in pairs])


def verify_one(stored_r: np.ndarray, stored_z: np.ndarray, stored_zero_var: np.ndarray,
               ts: np.ndarray, clip: float, rng: np.random.Generator,
               n_pairs: int = 200, use_nilearn: bool = True) -> dict:
    """Compare one participant's stored full matrices with independent recomputation."""
    r_ind = manual_pearson(ts)
    z_ind = manual_fisher(r_ind, clip)
    flat = np.isnan(r_ind).all(axis=0)

    np.fill_diagonal(r_ind, np.where(flat, np.nan, 1.0))
    nan_match = bool(np.array_equal(np.isnan(stored_r), np.isnan(r_ind))
                     and np.array_equal(flat, stored_zero_var))

    finite = np.isfinite(r_ind) & np.isfinite(stored_r)
    r_diff = float(np.max(np.abs(stored_r[finite] - r_ind[finite]))) if finite.any() else 0.0
    zf = np.isfinite(z_ind) & np.isfinite(stored_z)
    z_err = np.abs(stored_z[zf] - z_ind[zf])
    z_ok = bool(np.all(z_err <= Z_ATOL + Z_RTOL * np.abs(z_ind[zf])))
    z_diff = float(z_err.max()) if zf.any() else 0.0

    keep = np.flatnonzero(~flat)
    iu = np.triu_indices(len(keep), k=1)
    choose = rng.choice(len(iu[0]), size=min(n_pairs, len(iu[0])), replace=False)
    pairs = np.column_stack([keep[iu[0][choose]], keep[iu[1][choose]]])
    sp = scipy_pairs(ts, pairs)
    scipy_diff = float(np.max(np.abs(stored_r[pairs[:, 0], pairs[:, 1]] - sp)))

    nl_diff = float("nan")
    if use_nilearn:
        nl = nilearn_pearson(ts, keep)
        sub = stored_r[np.ix_(keep, keep)].copy()
        np.fill_diagonal(sub, 1.0)
        nl_diff = float(np.max(np.abs(sub - nl)))

    passed = (nan_match and r_diff <= R_ATOL and z_ok and scipy_diff <= R_ATOL
              and (not use_nilearn or nl_diff <= R_ATOL))
    return {"r_max_abs_diff_manual": r_diff, "r_max_abs_diff_scipy": scipy_diff,
            "r_max_abs_diff_nilearn": nl_diff, "z_max_abs_diff": z_diff,
            "nan_pattern_match": nan_match, "flat_regions": int(flat.sum()),
            "passed": bool(passed)}
