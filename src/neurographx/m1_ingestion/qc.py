"""Quality control screen, applied exactly as fixed in decision memo 0003.

Three gates, in order:

1. Rater criteria. The five rater columns must hold an accepted value.
2. Head motion. Mean framewise displacement must not exceed the threshold.
   A participant with no recorded motion value is excluded, because the gate
   cannot be shown to pass.
3. Completeness. Every configured atlas must have a region time series file
   on disk, and the file must contain at least two timepoints. Only checked for
   participants who pass the rater gate, because Week 1 downloaded time series
   for those participants only. Reporting "missing file" for someone who was
   never fetched would be true but misleading.

Every participant who fails is written to the exclusion log with the gate and
the reason. A participant can fail more than one gate; every reason is kept.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ID_COLUMNS = ["SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP"]


def rater_mask(df: pd.DataFrame, criteria: dict[str, list[str]]) -> pd.DataFrame:
    """One boolean column per rater column, True where the value is accepted."""
    out = {}
    for column, accepted in criteria.items():
        if column not in df.columns:
            raise KeyError(f"Rater column {column!r} is not in the phenotypic file")
        out[column] = df[column].astype("string").str.strip().isin(accepted).fillna(False)
    return pd.DataFrame(out, index=df.index)


def _timepoints(path: Path) -> int:
    """Count data rows in a .1D file without parsing the numbers."""
    with path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip() and not line.startswith("#"))


def completeness(file_ids: pd.Series, folder: Path, atlas_keys: list[str],
                 min_timepoints: int = 2) -> pd.DataFrame:
    """For each participant, the first completeness problem found, or empty."""
    problems = []
    for fid in file_ids:
        reason = ""
        if not isinstance(fid, str) or fid == "no_filename":
            reason = "no FILE_ID in the phenotypic file"
        else:
            for key in atlas_keys:
                p = folder / f"{fid}_{key}.1D"
                if not p.exists():
                    reason = f"missing {key} file"
                    break
                if _timepoints(p) < min_timepoints:
                    reason = f"empty or single-timepoint {key} file"
                    break
        problems.append(reason)
    return pd.DataFrame({"completeness_problem": problems}, index=file_ids.index)


def apply_qc(df: pd.DataFrame, qc_cfg: dict, folder: Path | None,
             atlas_keys: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (retained cohort, exclusion log).

    `folder` is the directory holding the region time series. Passing None skips
    the completeness gate, which is only done in tests.
    """
    reasons: dict[int, list[tuple[str, str]]] = {i: [] for i in df.index}

    raters = rater_mask(df, qc_cfg["rater_criteria"])
    for column in raters.columns:
        for i in raters.index[~raters[column]]:
            value = df.at[i, column]
            reasons[i].append(("rater", f"{column} = {value if pd.notna(value) else 'missing'}"))

    motion = qc_cfg["motion"]
    column = motion["column"]
    threshold = float(motion["mean_fd_max"])
    fd = pd.to_numeric(df[column], errors="coerce")
    for i in df.index[fd.isna()]:
        reasons[i].append(("motion", f"{column} missing"))
    for i in df.index[fd > threshold]:
        reasons[i].append(("motion", f"{column} = {fd[i]:.3f} > {threshold}"))

    if folder is not None and qc_cfg.get("completeness", {}).get("require_derivative_present"):
        passed_raters = raters.all(axis=1)
        comp = completeness(df.loc[passed_raters, "FILE_ID"], folder, atlas_keys)
        for i in comp.index[comp["completeness_problem"] != ""]:
            reasons[i].append(("completeness", comp.at[i, "completeness_problem"]))

    excluded_idx = [i for i, r in reasons.items() if r]
    log_rows = []
    for i in excluded_idx:
        gates = sorted({g for g, _ in reasons[i]}, key=["rater", "motion", "completeness"].index)
        log_rows.append({
            **{c: df.at[i, c] for c in ID_COLUMNS},
            "first_gate_failed": gates[0],
            "gates_failed": ";".join(gates),
            "reasons": "; ".join(r for _, r in reasons[i]),
        })
    log = pd.DataFrame(log_rows, columns=[*ID_COLUMNS, "first_gate_failed", "gates_failed",
                                          "reasons"])
    log = log.sort_values("SUB_ID").reset_index(drop=True)

    retained = df.drop(index=excluded_idx)[[*ID_COLUMNS, column]].copy()
    retained = retained.rename(columns={column: "mean_fd"})
    retained = retained.sort_values("SUB_ID").reset_index(drop=True)
    retained["SUB_ID"] = retained["SUB_ID"].astype(np.int64)
    retained["DX_GROUP"] = retained["DX_GROUP"].astype(np.int64)
    return retained, log


def gate_counts(log: pd.DataFrame, total: int) -> dict:
    """Counts for the memo: excluded at each gate (first failure) and retained."""
    first = log["first_gate_failed"].value_counts().to_dict() if len(log) else {}
    return {
        "total": int(total),
        "excluded_rater": int(first.get("rater", 0)),
        "excluded_motion": int(first.get("motion", 0)),
        "excluded_completeness": int(first.get("completeness", 0)),
        "retained": int(total - len(log)),
    }
