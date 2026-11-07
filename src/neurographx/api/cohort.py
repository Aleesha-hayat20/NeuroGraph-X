"""Cohort-level views the API serves (decision memo 0013, part 3; backlog W5-02).

    summary(records)        counts for the dashboard's Overview page (GET /cohort/summary)
    exclusion_records(...)  the exclusion log, one record per excluded participant (GET /exclusions)
    atlas_records(root)     the four atlases: size, data present, model registered (GET /atlases)

Everything is derived from files M1, M2 and the run logger already wrote; this module only
reshapes them. It reads the active dataset through neurographx.datasource, so it works the
same on real data and on the fixture (memo 0014).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from neurographx import datasource
from neurographx.m2_connectome.engine import atlas_paths
from neurographx.m3_model.run_logger import read_registry

GATES = ("rater", "motion", "completeness")  # memo 0003, in the order they are applied


def atlas_name(atlas_key: str) -> str:
    """'rois_cc200' -> 'cc200', the name used by the registry, the API and the dashboard."""
    return atlas_key.removeprefix("rois_")


# ---------------------------------------------------------------------------
# Cohort summary
# ---------------------------------------------------------------------------

def summary(records: list[dict]) -> dict:
    """Counts for the Overview page. Excluded participants are counted at the first gate
    they failed, the same rule as memo 0003's table and the QC script."""
    included = [r for r in records if r["qc_status"] == "included"]
    excluded = [r for r in records if r["qc_status"] == "excluded"]
    first_gate = Counter(r["exclusion_gate"] for r in excluded)

    by_group = {}
    for group in ("autism", "control"):
        by_group[group] = {
            "included": sum(r["group"] == group for r in included),
            "excluded": sum(r["group"] == group for r in excluded),
        }
    sites = sorted({r["site"] for r in records if r["site"] is not None})
    by_site = [{"site": s,
                "included": sum(r["site"] == s for r in included),
                "excluded": sum(r["site"] == s for r in excluded)} for s in sites]
    split = Counter(r["split"] for r in included)
    return {
        "total": len(records),
        "included": len(included),
        "excluded": len(excluded),
        "excluded_by_gate": {g: first_gate.get(g, 0) for g in GATES},
        "by_group": by_group,
        "by_site": by_site,
        "by_split": {"frozen": split.get("frozen", 0),
                     "development": split.get("development", 0)},
    }


# ---------------------------------------------------------------------------
# Exclusion log
# ---------------------------------------------------------------------------

def exclusion_records(records: list[dict], gate: str | None = None) -> list[dict]:
    """Excluded participants with the first gate failed, every gate failed and every reason.

    `gate` keeps only participants whose FIRST failed gate is that one, so the counts
    match the excluded_by_gate figures of the summary.
    """
    out = []
    for r in records:
        if r["qc_status"] != "excluded":
            continue
        if gate is not None and r["exclusion_gate"] != gate:
            continue
        out.append({
            "participant_id": r["participant_id"],
            "file_id": r["file_id"],
            "site": r["site"],
            "group": r["group"],
            "first_gate_failed": r["exclusion_gate"],
            "gates_failed": list(r["gates_failed"]),
            "reasons": list(r["exclusion_reasons"]),
        })
    return out


# ---------------------------------------------------------------------------
# Atlases
# ---------------------------------------------------------------------------

def atlas_records(root: Path | None = None) -> list[dict]:
    """The configured atlases, in config order, each with what the dashboard needs to know.

    data_available: the connectome .npz and its manifest are both present.
    n_regions:      from the manifest (None when the data is not available).
    model_registered and run_id: from the model registry. Whether the checkpoint FILE is
    present is checked when an analysis is requested (analysis_checks.py), not here.
    """
    cfg = datasource.data_config(root)
    pipeline, strategy = cfg["pipeline"]["name"], cfg["pipeline"]["strategy"]
    registry = read_registry(datasource.model_registry(root))
    out = []
    for atlas in cfg["atlases"]:
        key = atlas["key"]
        name = atlas_name(key)
        npz, manifest_path = atlas_paths(datasource.connectome_dir(root), pipeline, strategy,
                                         key)
        n_regions = None
        available = npz.exists() and manifest_path.exists()
        if available:
            try:
                n_regions = int(json.loads(manifest_path.read_text(encoding="utf-8"))
                                ["n_regions"])
            except (ValueError, KeyError):
                available = False  # an unreadable manifest is treated as missing data
        entry = registry.get(name)
        out.append({
            "atlas": name,
            "key": key,
            "label": atlas.get("label", name),
            "family": atlas.get("family"),
            "n_regions": n_regions,
            "data_available": available,
            "model_registered": entry is not None,
            "run_id": entry["run_id"] if entry else None,
        })
    return out


def atlas_names(root: Path | None = None) -> list[str]:
    """['aal', 'cc200', 'ho', 'dosenbach160'] for the active dataset, in config order."""
    return [atlas_name(a["key"]) for a in datasource.data_config(root)["atlases"]]
