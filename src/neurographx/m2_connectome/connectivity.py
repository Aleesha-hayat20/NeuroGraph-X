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


# ---------------------------------------------------------------------------
# Week 2: Fisher transform and compact storage helpers
# ---------------------------------------------------------------------------

DEFAULT_FISHER_CLIP = 0.9999999


def fisher_z(corr: np.ndarray, clip: float = DEFAULT_FISHER_CLIP) -> np.ndarray:
    """Fisher r-to-z transform, z = arctanh(r) = 0.5 * ln((1 + r) / (1 - r)).

    Why: Pearson r is bounded in [-1, 1] and its sampling distribution is skewed
    near the bounds. z is unbounded and approximately normal, so averages and
    differences of z behave well, which is what a model and later statistics need.

    Conventions, recorded in decision memo 0007:
    - |r| is clipped to `clip` first, because arctanh(1) is infinite.
    - The diagonal (a region with itself) is set to 0. It carries no information
      and an infinite value would poison any downstream sum.
    - NaN stays NaN. Those cells belong to zero-variance regions and are tracked
      separately by a mask; filling them is a modelling decision, not this one.
    """
    if not 0 < clip < 1:
        raise ValueError(f"clip must be in (0, 1), got {clip}")
    z = np.arctanh(np.clip(corr, -clip, clip))
    if z.ndim == 2 and z.shape[0] == z.shape[1]:
        np.fill_diagonal(z, 0.0)
    return z


def triu_indices(n_regions: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices of the strict upper triangle, row-major, the storage order used on disk."""
    return np.triu_indices(n_regions, k=1)


def to_triu(matrix: np.ndarray) -> np.ndarray:
    """Square symmetric matrix to its strict upper triangle as a 1D vector."""
    return matrix[triu_indices(matrix.shape[0])]


def from_triu(vector: np.ndarray, n_regions: int, diagonal: float) -> np.ndarray:
    """Rebuild a full symmetric matrix from its strict upper triangle."""
    expected = n_regions * (n_regions - 1) // 2
    if vector.shape[-1] != expected:
        raise ValueError(f"Vector length {vector.shape[-1]} does not fit {n_regions} regions")
    out = np.empty((n_regions, n_regions), dtype=vector.dtype)
    iu = triu_indices(n_regions)
    out[iu] = vector
    out[(iu[1], iu[0])] = vector
    np.fill_diagonal(out, diagonal)
    return out


def n_regions_from_edges(n_edges: int) -> int:
    """Invert n * (n - 1) / 2 = n_edges."""
    n = int(round((1 + np.sqrt(1 + 8 * n_edges)) / 2))
    if n * (n - 1) // 2 != n_edges:
        raise ValueError(f"{n_edges} is not a triangular number of edges")
    return n
