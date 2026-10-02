"""Summarise downloaded region time series, one atlas at a time.

Produces the facts needed to close decision memo 0001: the real region count
per atlas, the timepoint range, zero variance regions, and disk usage.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

from neurographx.m2_connectome import connectivity as cx


def summarise_atlas(key: str, label: str, family: str, arrays: list, file_ids: list,
                    folder: Path) -> dict:
    regions, timepoints = [], []
    with_zero_var, zero_var_total, invalid, size_bytes = 0, 0, 0, 0

    for fid, ts in zip(file_ids, arrays):
        ts = np.asarray(ts)
        if ts.ndim == 1:
            ts = ts.reshape(1, -1)
        regions.append(ts.shape[1])
        timepoints.append(ts.shape[0])
        zv = cx.zero_variance_regions(ts)
        if len(zv):
            with_zero_var += 1
            zero_var_total += len(zv)
        if not cx.is_valid(cx.check_matrix(cx.correlation_matrix(ts), zv)):
            invalid += 1
        p = folder / f"{fid}_{key}.1D"
        if p.exists():
            size_bytes += p.stat().st_size

    counts = Counter(regions)
    modal_regions = counts.most_common(1)[0][0] if counts else 0
    tp = np.array(timepoints) if timepoints else np.array([0])
    return {
        "key": key,
        "label": label,
        "family": family,
        "participants": len(arrays),
        "regions": modal_regions,
        "regions_consistent": len(counts) == 1,
        "region_counts_seen": dict(counts),
        "timepoints_min": int(tp.min()),
        "timepoints_median": int(np.median(tp)),
        "timepoints_max": int(tp.max()),
        "participants_with_zero_variance": with_zero_var,
        "zero_variance_region_total": zero_var_total,
        "invalid_matrices": invalid,
        "size_mb": round(size_bytes / 1e6, 1),
        "file_ids": list(file_ids),
    }


def render(rows: list[dict], meta: dict) -> str:
    same_set = len({tuple(r["file_ids"]) for r in rows}) == 1
    total_mb = round(sum(r["size_mb"] for r in rows), 1)

    lines = [
        "# Atlas Download Summary",
        "",
        f"**Generated:** {meta['date']}  ",
        f"**Pipeline:** {meta['pipeline']}  **Strategy:** {meta['strategy']}  ",
        "**Quality filter:** nilearn `quality_checked=True`, all five rater columns  ",
        f"**nilearn version:** {meta['nilearn']}",
        "",
        "This file closes the open items in `docs/decisions/0001-atlas-selection.md`.",
        "",
        "## Per atlas",
        "",
        "| Atlas | Family | Participants | Regions (nodes) | Timepoints min / median / max "
        "| With zero-variance regions | Invalid matrices | Size on disk |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        regions = str(r["regions"]) if r["regions_consistent"] else \
            f"{r['regions']} (inconsistent: {r['region_counts_seen']})"
        lines.append(
            f"| {r['label']} | {r['family']} | {r['participants']} | {regions} | "
            f"{r['timepoints_min']} / {r['timepoints_median']} / {r['timepoints_max']} | "
            f"{r['participants_with_zero_variance']} | {r['invalid_matrices']} | "
            f"{r['size_mb']} MB |"
        )
    lines += [
        "",
        "## Checks",
        "",
        f"- Same participant set across all four atlases: **{'yes' if same_set else 'NO'}**",
        f"- Total size on disk: **{total_mb} MB**",
        f"- Invalid matrices across all atlases: "
        f"**{sum(r['invalid_matrices'] for r in rows)}**",
        "",
        "## Notes for the connectome engine",
        "",
        "- **Regions** is the number of graph nodes, and so the model's input dimension. "
        "It differs per atlas, which is why decision 0004 trains one model per atlas.",
        "- **Zero-variance regions** produce NaN rows and columns in the correlation matrix. "
        "They are counted as valid here because the NaNs are fully explained, but the "
        "connectome engine must decide how to handle them before any model is trained. "
        "That decision needs its own memo.",
        "- **Timepoints** vary because sites used different scan lengths and repetition "
        "times. Correlation is computed per participant, so the matrices are comparable "
        "even when the time series lengths are not.",
        "",
    ]
    return "\n".join(lines)
