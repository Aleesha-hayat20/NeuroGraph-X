"""Region time series to connectivity matrix, with diagnostics.

This is the seed of the M2 connectome engine. Week 1 uses it to verify the
pilot atlas. Week 2 extends it with the Fisher transform, storage and caching.

Shape convention used everywhere in this project:
    time series     (timepoints, regions)   one column per brain region
    connectivity    (regions, regions)      square, symmetric
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

ZERO_VARIANCE_TOL = 1e-10


def load_1d(path: Path) -> np.ndarray:
    """Load one ABIDE region time series file.

    The .1D files carry a header line starting with '#', which numpy skips.
    A file with a single timepoint would load as 1D, so it is reshaped to 2D
    and left for the caller's checks to reject.
    """
    ts = np.loadtxt(path)
    if ts.ndim == 1:
        ts = ts.reshape(1, -1)
    return ts


def zero_variance_regions(ts: np.ndarray, tol: float = ZERO_VARIANCE_TOL) -> np.ndarray:
    """Indices of regions whose signal never changes.

    These usually fall outside the scanner's acquired field of view for that
    participant. Their correlation with anything is undefined, so they come
    back from the correlation as NaN.
    """
    return np.where(ts.std(axis=0) < tol)[0]


def correlation_matrix(ts: np.ndarray) -> np.ndarray:
    """Region by region Pearson correlation.

    rowvar=False is essential. numpy's default treats each ROW as a variable,
    and our rows are timepoints, so the default would silently return a
    timepoint by timepoint matrix that is square and completely wrong.
    """
    if ts.ndim != 2:
        raise ValueError(f"Expected a 2D (timepoints, regions) array, got shape {ts.shape}")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.corrcoef(ts, rowvar=False)


def check_matrix(corr: np.ndarray, zero_var: np.ndarray | None = None) -> dict:
    """Validity checks on a connectivity matrix.

    The diagonal check excludes zero variance regions, whose diagonal entry is
    NaN by construction. Every other diagonal entry must equal one.
    """
    diag = np.diag(corr)
    finite = ~np.isnan(diag)
    nan_cells = int(np.isnan(corr).sum())

    explained = None
    if zero_var is not None:
        n, k = corr.shape[0], len(zero_var)
        expected = n * n - (n - k) * (n - k)
        explained = nan_cells == expected

    return {
        "shape": tuple(corr.shape),
        "square": corr.ndim == 2 and corr.shape[0] == corr.shape[1],
        "symmetric": bool(np.allclose(corr, corr.T, equal_nan=True)),
        "diagonal_ones": bool(np.allclose(diag[finite], 1.0)) if finite.any() else False,
        "nan_cells": nan_cells,
        "nan_explained_by_zero_variance": explained,
        "min": float(np.nanmin(corr)) if np.isfinite(corr).any() else float("nan"),
        "max": float(np.nanmax(corr)) if np.isfinite(corr).any() else float("nan"),
    }


def is_valid(report: dict) -> bool:
    """True when the matrix passes every structural check."""
    in_range = -1.0 - 1e-9 <= report["min"] and report["max"] <= 1.0 + 1e-9
    nan_ok = report["nan_cells"] == 0 or report["nan_explained_by_zero_variance"] is True
    return report["square"] and report["symmetric"] and report["diagonal_ones"] \
        and in_range and nan_ok
