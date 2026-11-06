"""Confidence calibration (memo 0010): Platt scaling fitted on out-of-fold predictions.

The model's probability of autism `p` is mapped to a calibrated probability

    q = sigmoid(a * logit(p) + b)

with two numbers per atlas, fitted by logistic regression on the OOF table of the
cross-validation run whose settings the final model used. `a` stretches or shrinks
over- and under-confidence; `b` corrects a lean towards one class. Because the map is
increasing (a > 0 in practice), the order of participants, and so the AUC, never changes.

What is never used: the frozen set. It is only *scored* before and after, from the one
set of frozen predictions the final stage already saved (memo 0010, section 4), so this
is not a second measurement.

How it is judged (memo 0010, section 4):
- ECE, 10 equal-width bins of the probability of autism over 0 to 1;
- Brier score;
- reliability table (and figure): per bin, mean probability against observed share.
On OOF the "after" numbers are cross-fitted: fit on four folds, score the fifth, rotate,
so the calibrator is never scored on rows it was fitted on.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

METHOD = "platt"
CALIBRATION_DIR = Path("runs/calibration")
N_BINS = 10
EPS = 1e-6  # keeps logit(p) finite for p = 0 or 1


def calibration_path(atlas: str, run_id: str, folder: Path = CALIBRATION_DIR) -> Path:
    """runs/calibration/<atlas>_<final run_id>.json (memo 0010, section 5)."""
    return Path(folder) / f"{atlas}_{run_id}.json"


# ---------------------------------------------------------------------------
# The calibrator
# ---------------------------------------------------------------------------

def _logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _sigmoid(z) -> np.ndarray:
    # exp(-logaddexp(0, -z)) = 1 / (1 + exp(-z)), without overflow for large |z|
    return np.exp(-np.logaddexp(0.0, -np.asarray(z, dtype=float)))


def fit_platt(prob, label, max_iter: int = 100, tol: float = 1e-10) -> tuple[float, float]:
    """Fit (a, b) by maximum likelihood: logistic regression of `label` on logit(`prob`).

    Newton's method on two parameters, with step halving so every step lowers the
    negative log-likelihood (plain Newton can overshoot and diverge when the model is
    very over-confident, as real OOF tables are). Deterministic: starts at the identity
    map, no random start, no library defaults. A tiny ridge (1e-6) keeps it finite if
    the two classes are perfectly separated, which can happen on a toy table.
    """
    x = _logit(prob)
    y = np.asarray(label, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or len(x) < 2:
        raise ValueError("prob and label must be 1-D arrays of the same length (at least 2)")
    if not set(np.unique(y)) <= {0.0, 1.0}:
        raise ValueError("label must be 0 (control) or 1 (autism)")
    if len(np.unique(y)) < 2:
        raise ValueError("calibration needs both classes in the fitting data")
    X = np.column_stack([x, np.ones_like(x)])
    ridge = 1e-6

    def loss(w):  # negative log-likelihood, computed without overflow
        z = X @ w
        return float(np.sum(np.logaddexp(0.0, z) - y * z) + 0.5 * ridge * w @ w)

    w = np.array([1.0, 0.0])  # start at the identity map q = p
    current = loss(w)
    for _ in range(max_iter):
        q = _sigmoid(X @ w)
        grad = X.T @ (q - y) + ridge * w
        hess = X.T @ (X * (q * (1 - q))[:, None]) + ridge * np.eye(2)
        step = np.linalg.solve(hess, grad)
        t = 1.0
        while t > 1e-10:
            candidate = w - t * step
            new = loss(candidate)
            if new <= current:
                break
            t /= 2
        else:
            break  # no step lowers the loss: at the optimum within rounding
        moved = float(np.abs(candidate - w).max())
        w, current = candidate, new
        if moved < tol:
            break
    return float(w[0]), float(w[1])


def apply_platt(prob, a: float, b: float) -> np.ndarray:
    """Calibrated probability of autism."""
    return _sigmoid(a * _logit(prob) + b)


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------

def _bin_index(prob: np.ndarray, n_bins: int) -> np.ndarray:
    # equal-width bins over [0, 1]; p = 1.0 belongs to the last bin
    return np.minimum((prob * n_bins).astype(int), n_bins - 1)


def reliability_table(prob, label, n_bins: int = N_BINS) -> list[dict]:
    """One row per non-empty bin: range, count, mean probability, observed share of autism."""
    prob = np.asarray(prob, dtype=float)
    label = np.asarray(label, dtype=float)
    idx = _bin_index(prob, n_bins)
    rows = []
    for k in range(n_bins):
        mask = idx == k
        if mask.any():
            rows.append({"lower": round(k / n_bins, 4), "upper": round((k + 1) / n_bins, 4),
                         "n": int(mask.sum()),
                         "mean_prob": round(float(prob[mask].mean()), 4),
                         "observed": round(float(label[mask].mean()), 4)})
    return rows


def ece(prob, label, n_bins: int = N_BINS) -> float:
    """Expected calibration error: size-weighted mean |mean probability - observed share|."""
    prob = np.asarray(prob, dtype=float)
    label = np.asarray(label, dtype=float)
    idx = _bin_index(prob, n_bins)
    total = 0.0
    for k in range(n_bins):
        mask = idx == k
        if mask.any():
            total += mask.sum() * abs(prob[mask].mean() - label[mask].mean())
    return float(total / len(prob))


def brier(prob, label) -> float:
    prob = np.asarray(prob, dtype=float)
    label = np.asarray(label, dtype=float)
    return float(np.mean((prob - label) ** 2))


def _scores(prob, label) -> dict:
    return {"ece": round(ece(prob, label), 4), "brier": round(brier(prob, label), 4)}


def cross_fitted(oof: pd.DataFrame) -> np.ndarray:
    """Calibrated OOF probabilities, each row from a calibrator fitted on the OTHER folds."""
    out = np.empty(len(oof))
    folds = oof["fold"].to_numpy()
    prob = oof["prob_autism"].to_numpy(dtype=float)
    label = oof["label"].to_numpy(dtype=int)
    for f in np.unique(folds):
        held = folds == f
        a, b = fit_platt(prob[~held], label[~held])
        out[held] = apply_platt(prob[held], a, b)
    return out


# ---------------------------------------------------------------------------
# The whole procedure for one final model
# ---------------------------------------------------------------------------

def calibrate(oof: pd.DataFrame, frozen_predictions: pd.DataFrame | None = None) -> dict:
    """Fit on all OOF rows; report OOF (cross-fitted) and frozen scores before and after.

    `oof` must already have passed `oof.check_oof` (the script does this). Returns the
    numbers for the calibration file, without the identifying fields the caller adds.
    """
    prob = oof["prob_autism"].to_numpy(dtype=float)
    label = oof["label"].to_numpy(dtype=int)
    a, b = fit_platt(prob, label)
    if a <= 0:
        # a <= 0 would reverse (or erase) the model's ranking: its OOF predictions are no
        # better than chance, so there is nothing to calibrate. Report it, do not hide it.
        raise ValueError(f"Platt slope a = {a:.4f} <= 0: calibrating would reverse the model's "
                         "ranking (its out-of-fold predictions rank no better than chance); "
                         "no calibration file written")
    after_cf = cross_fitted(oof)
    result = {
        "method": METHOD,
        "a": round(a, 6),
        "b": round(b, 6),
        "n": int(len(oof)),
        "oof": {"before": _scores(prob, label), "after_cross_fitted": _scores(after_cf, label),
                "reliability_before": reliability_table(prob, label),
                "reliability_after": reliability_table(after_cf, label)},
        "frozen": None,
    }
    if frozen_predictions is not None:
        fp = frozen_predictions["prob_autism"].to_numpy(dtype=float)
        fl = frozen_predictions["label"].to_numpy(dtype=int)
        fq = apply_platt(fp, a, b)
        result["frozen"] = {
            "n": int(len(fp)),
            "before": _scores(fp, fl),
            "after": _scores(fq, fl),
            # Platt scaling keeps the order (AUC unchanged) but can move the 0.5 threshold
            "prediction_flips": int(((fp >= 0.5) != (fq >= 0.5)).sum()),
            "accuracy_before": round(float(((fp >= 0.5) == fl).mean()), 4),
            "accuracy_after": round(float(((fq >= 0.5) == fl).mean()), 4),
            "reliability_before": reliability_table(fp, fl),
            "reliability_after": reliability_table(fq, fl),
        }
    return result


def write_calibration(record: dict, path: Path) -> None:
    """Write the calibration file. A file is never overwritten: one calibrator per run."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; a calibration file is written once per run")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {**record, "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_calibration(path: Path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("method") != METHOD:
        raise ValueError(f"{path}: unknown calibration method {record.get('method')!r}")
    return record


def reliability_figure(record: dict, path: Path, title: str) -> None:
    """Reliability diagram: OOF (cross-fitted) and, if present, frozen; before and after."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    panels = [("Out-of-fold (development, cross-fitted)", record["oof"]["reliability_before"],
               record["oof"]["reliability_after"])]
    if record.get("frozen"):
        panels.append(("Frozen set (100, never fitted on)", record["frozen"]["reliability_before"],
                       record["frozen"]["reliability_after"]))
    fig, axes = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 5), squeeze=False)
    for ax, (name, before, after) in zip(axes[0], panels):
        ax.plot([0, 1], [0, 1], linestyle="--", color="grey", linewidth=1, label="perfect")
        for rows, label, marker in ((before, "before", "o"), (after, "after (Platt)", "s")):
            ax.plot([r["mean_prob"] for r in rows], [r["observed"] for r in rows],
                    marker=marker, label=label)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Mean predicted probability of autism (bin)")
        ax.set_ylabel("Observed share of autism (bin)")
        ax.set_title(name, fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
