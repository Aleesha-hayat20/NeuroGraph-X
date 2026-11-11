"""Confound check on the out-of-fold predictions (work plan, Week 6; Section 7 item A6).

A confound is something other than the diagnosis that differs between the groups and that
the model could learn instead of the diagnosis. Three are well known for ABIDE resting-state
connectomes:

- **Site.** Each site used its own scanner and protocol, and the share of autistic
  participants differs between sites, so a model can partly recognise the site.
- **Head motion.** Movement in the scanner changes measured connectivity, and on average
  the autism group moves more. Quality control already excluded mean framewise
  displacement (FD) above 0.5 mm (memo 0003); some motion remains.
- **Flat regions.** Regions outside a scan's field of view have a constant signal and no
  correlation (memo 0007). They follow the scanner, so they track site.

This module describes how accuracy varies along each of these, using the out-of-fold
(OOF) predictions of the cross-validation run each registered model was selected from:
every development participant is predicted once by a model that did not train on them
(memo 0010). It reads no frozen-set file and fits nothing. The result is a limitation
analysis for the report: it shows where the accuracy is uneven, it does not show what the
models learned.

Predictions are the raw (uncalibrated) OOF probabilities at the 0.5 threshold, the same
rule the cross-validation accuracy uses.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from neurographx import datasource
from neurographx.integrity import text_hash_matches

ATLAS_ORDER = ("cc200", "aal", "ho", "dosenbach160")
QUARTILES = ("Q1 (least motion)", "Q2", "Q3", "Q4 (most motion)")


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------

def scores(label: np.ndarray, prediction: np.ndarray) -> dict:
    """n, accuracy, balanced accuracy (None when a group has one class) and shares."""
    label, prediction = np.asarray(label, int), np.asarray(prediction, int)
    n = len(label)
    if n == 0:
        return {"n": 0, "accuracy": None, "balanced_accuracy": None,
                "autism_share": None, "predicted_autism_share": None}
    correct = label == prediction
    recalls = [correct[label == c].mean() for c in (0, 1) if (label == c).any()]
    return {
        "n": int(n),
        "accuracy": float(correct.mean()),
        "balanced_accuracy": float(np.mean(recalls)) if len(recalls) == 2 else None,
        "autism_share": float(label.mean()),
        "predicted_autism_share": float(prediction.mean()),
    }


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n (a standard interval for accuracy)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

class ConfoundInputError(ValueError):
    """An input file is missing or does not match the run log."""


def _runs(root: Path) -> dict[str, dict]:
    path = datasource.run_log(root)
    return {r["run_id"]: r for r in (json.loads(x) for x in
                                     path.read_text(encoding="utf-8").splitlines()
                                     if x.strip())}


def selected_oof(root: Path | None = None) -> dict[str, dict]:
    """For each registered atlas: its final run, its cv run, and the checked OOF table."""
    root = Path(root) if root is not None else datasource.data_root()
    registry = json.loads(datasource.model_registry(root).read_text(encoding="utf-8"))
    runs = _runs(root)
    out = {}
    for atlas in [a for a in ATLAS_ORDER if a in registry] + \
            sorted(set(registry) - set(ATLAS_ORDER)):
        final = runs.get(registry[atlas]["run_id"])
        cv_id = ((final or {}).get("metrics") or {}).get("cv_run_id")
        cv = runs.get(cv_id) if cv_id else None
        meta = ((cv or {}).get("metrics") or {}).get("oof")
        if not meta:
            raise ConfoundInputError(f"{atlas}: the cross-validation run of the registered "
                                     "model saved no out-of-fold file")
        path = datasource.checkpoint(meta["file"], root)  # relative to the data root
        if not path.exists() or not text_hash_matches(path, meta["sha256"]):
            raise ConfoundInputError(f"{atlas}: {meta['file']} is missing or does not match "
                                     "the run log")
        out[atlas] = {"final_run": final["run_id"], "cv_run": cv_id,
                      "atlas_key": cv["data_config"]["atlas_key"],
                      "oof": pd.read_csv(path)}
    return out


def development_pool(root: Path | None = None) -> pd.DataFrame:
    """The development folds with each participant's mean FD from the QC cohort."""
    root = Path(root) if root is not None else datasource.data_root()
    folds = pd.read_csv(datasource.cv_folds(root))
    cohort = pd.read_csv(datasource.qc_cohort(root))
    fd = "mean_fd" if "mean_fd" in cohort.columns else "func_mean_fd"
    pool = folds.merge(cohort[["SUB_ID", fd]].rename(columns={fd: "mean_fd"}),
                       on="SUB_ID", how="left", validate="one_to_one")
    if pool["mean_fd"].isna().any():
        raise ConfoundInputError("some development participants have no mean FD in the "
                                 "QC cohort")
    return pool


def flat_region_counts(root: Path, atlas_key: str, file_ids) -> np.ndarray:
    """Flat (zero-variance) regions per participant, from the connectome store."""
    from neurographx.m2_connectome.engine import atlas_paths, load_atlas

    pipeline = datasource.data_config(root)["pipeline"]
    npz, manifest = atlas_paths(datasource.connectome_dir(root), pipeline["name"],
                                pipeline["strategy"], atlas_key)
    cset = load_atlas(npz, manifest)
    return np.array([int(cset.zero_var[cset.index(str(f))].sum()) for f in file_ids])


# ---------------------------------------------------------------------------
# The analysis
# ---------------------------------------------------------------------------

def analyse(root: Path | None = None, with_flat_regions: bool = True) -> dict:
    """Every table of the report, as plain data (the renderer only formats it)."""
    root = Path(root) if root is not None else datasource.data_root()
    selected = selected_oof(root)
    pool = development_pool(root)
    quartile = pd.qcut(pool["mean_fd"], 4, labels=list(QUARTILES))
    pool = pool.assign(quartile=quartile.astype(str))
    edges = pool.groupby("quartile", observed=True)["mean_fd"].agg(["min", "max"])

    result = {"n": len(pool), "atlases": {}, "sites": [], "quartiles": [],
              "motion_by_group": {}}
    merged = {}
    for atlas, sel in selected.items():
        oof = sel["oof"][["SUB_ID", "label", "prediction"]]
        m = pool.merge(oof, on="SUB_ID", how="inner", validate="one_to_one")
        if len(m) != len(pool):
            raise ConfoundInputError(f"{atlas}: the OOF file covers {len(m)} of the "
                                     f"{len(pool)} development participants")
        merged[atlas] = m
        result["atlases"][atlas] = {
            "final_run": sel["final_run"], "cv_run": sel["cv_run"],
            "overall": scores(m["label"], m["prediction"]),
            "majority_baseline": float(max(m["label"].mean(), 1 - m["label"].mean())),
        }
        if with_flat_regions:
            counts = flat_region_counts(root, sel["atlas_key"], m["FILE_ID"])
            m["flat"] = counts
            groups = {}
            for name, value in (("autism", 1), ("control", 0)):
                c = counts[m["label"].to_numpy() == value]
                groups[name] = {"n": int(len(c)), "with_flat": int((c > 0).sum()),
                                "mean_flat": float(c.mean()) if len(c) else 0.0}
            has = m["flat"] > 0
            result["atlases"][atlas]["flat"] = {
                "atlas_key": sel["atlas_key"], "by_group": groups,
                "with": scores(m.loc[has, "label"], m.loc[has, "prediction"]),
                "without": scores(m.loc[~has, "label"], m.loc[~has, "prediction"]),
            }

    first = next(iter(merged.values()))
    for site, rows in first.groupby("SITE_ID"):
        entry = {"site": site, "n": len(rows), "autism_share": float(rows["label"].mean()),
                 "by_atlas": {}}
        for atlas, m in merged.items():
            r = m[m["SITE_ID"] == site]
            entry["by_atlas"][atlas] = scores(r["label"], r["prediction"])
        result["sites"].append(entry)
    result["sites"].sort(key=lambda e: (-e["n"], e["site"]))

    for q in QUARTILES:
        rows = first[first["quartile"] == q]
        entry = {"quartile": q, "n": len(rows), "fd_min": float(edges.loc[q, "min"]),
                 "fd_max": float(edges.loc[q, "max"]),
                 "autism_share": float(rows["label"].mean()), "by_atlas": {}}
        for atlas, m in merged.items():
            r = m[m["quartile"] == q]
            entry["by_atlas"][atlas] = scores(r["label"], r["prediction"])
        result["quartiles"].append(entry)

    for name, value in (("autism", 1), ("control", 0)):
        fd = first.loc[first["label"] == value, "mean_fd"]
        result["motion_by_group"][name] = {"n": int(len(fd)), "median": float(fd.median()),
                                           "mean": float(fd.mean())}
    return result


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _f(value, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _pct(value) -> str:
    return "n/a" if value is None else f"{100 * value:.0f}%"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" if i == 0 else "---:" for i in range(len(header))) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines


def render(result: dict, generated: str, source: str) -> str:
    """docs/reports/confound_check.md from the output of analyse()."""
    atlases = list(result["atlases"])
    labels = {"cc200": "CC200", "aal": "AAL", "ho": "HO", "dosenbach160": "Dosenbach 160"}
    names = [labels.get(a, a) for a in atlases]
    out = [
        "# Confound check on the out-of-fold predictions",
        "",
        f"Generated by `scripts/confound_check.py` on {generated} from {source}. "
        "Do not edit by hand; run the script again instead.",
        "",
        "**What this is.** A limitation analysis for the report (work plan, Week 6): how the "
        "cross-validation accuracy of the four selected models varies by imaging site, by head "
        "motion, and with flat regions. **What this is not.** A finding about autism or about "
        "what the models learned: the groups below are small, they overlap (site, motion and "
        "flat regions are related), and no test is run.",
        "",
        f"**Data.** The {result['n']} development participants, each predicted once by a "
        "cross-validation model that did not train on them (out-of-fold, memo 0010). Raw "
        "probabilities at the 0.5 threshold, the rule behind the cross-validation accuracy. "
        "The frozen set is not read.",
        "",
        "## 1. Overall",
        "",
    ]
    rows = []
    for atlas, name in zip(atlases, names, strict=True):
        a = result["atlases"][atlas]
        o = a["overall"]
        rows.append([name, f"`{a['final_run']}`", f"`{a['cv_run']}`", str(o["n"]),
                     _f(o["accuracy"]), _f(o["balanced_accuracy"]),
                     _f(a["majority_baseline"])])
    out += _table(["Atlas", "Final run", "OOF from cv run", "n", "Accuracy",
                   "Balanced accuracy", "Majority baseline"], rows)

    # Sites -----------------------------------------------------------------
    sites = result["sites"]
    ns = sorted(e["n"] for e in sites)
    small, typical = ns[0], int(round(float(np.median(ns))))

    def half_width(n: int) -> float:
        k = round(0.65 * n)
        lo, hi = wilson_interval(k, n)
        return (hi - lo) / 2

    out += [
        "",
        "## 2. Accuracy by imaging site",
        "",
        f"{len(sites)} sites, from {small} to {ns[-1]} development participants. Per-site "
        f"numbers are noisy: for an accuracy of about 0.65 the 95% interval (Wilson) is "
        f"about ±{half_width(small):.2f} at n = {small} and ±{half_width(typical):.2f} at "
        f"n = {typical}, the median site size. The majority baseline differs by "
        "site because the share of autistic participants does.",
        "",
    ]
    rows = []
    for e in sites:
        majority = max(e["autism_share"], 1 - e["autism_share"])
        rows.append([e["site"], str(e["n"]), _pct(e["autism_share"]), _f(majority, 2)]
                    + [_f(e["by_atlas"][a]["accuracy"], 2) for a in atlases])
    out += _table(["Site", "n", "Autism", "Majority baseline", *names], rows)
    out += ["", "Spread of site accuracy per atlas:", ""]
    rows = []
    for atlas, name in zip(atlases, names, strict=True):
        accs = [(e["by_atlas"][atlas]["accuracy"], e["site"]) for e in sites]
        below = sum(acc < max(e["autism_share"], 1 - e["autism_share"])
                    for (acc, _), e in zip(accs, sites, strict=True))
        lo, hi = min(accs), max(accs)
        rows.append([name, f"{_f(lo[0], 2)} ({lo[1]})", f"{_f(hi[0], 2)} ({hi[1]})",
                     f"{below} of {len(sites)}"])
    out += _table(["Atlas", "Lowest site", "Highest site", "Sites below their baseline"],
                  rows)

    # Motion ----------------------------------------------------------------
    g = result["motion_by_group"]
    out += [
        "",
        "## 3. Accuracy by head motion",
        "",
        "Quartiles of mean framewise displacement (FD, mm) over the development pool. Quality "
        "control already removed mean FD above 0.5 mm (memo 0003), so this is the motion that "
        f"remains. Median mean FD: autism {g['autism']['median']:.3f} mm "
        f"(n = {g['autism']['n']}), control {g['control']['median']:.3f} mm "
        f"(n = {g['control']['n']}).",
        "",
    ]
    rows = []
    for q in result["quartiles"]:
        rows.append([q["quartile"], f"{q['fd_min']:.3f} to {q['fd_max']:.3f}", str(q["n"]),
                     _pct(q["autism_share"])]
                    + [_f(q["by_atlas"][a]["accuracy"], 2) for a in atlases])
    out += _table(["Quartile", "Mean FD (mm)", "n", "Autism", *names], rows)
    rows = []
    for q in result["quartiles"]:
        rows.append([q["quartile"]] + [_f(q["by_atlas"][a]["balanced_accuracy"], 2)
                                       for a in atlases])
    out += ["", "Balanced accuracy (the mean of the accuracy on each group), which does not "
                "change with the autism share of the quartile:", ""]
    out += _table(["Quartile", *names], rows)

    # Flat regions ----------------------------------------------------------
    if all("flat" in result["atlases"][a] for a in atlases):
        out += [
            "",
            "## 4. Flat regions by group",
            "",
            "Participants with at least one flat (zero-variance) region in the atlas, and the "
            "mean number of flat regions, per group; then the accuracy for participants with "
            "and without any. The graphs fill flat regions with 0 (`fill_nan` in each run's "
            "configuration, memo 0007).",
            "",
        ]
        rows = []
        for atlas, name in zip(atlases, names, strict=True):
            f = result["atlases"][atlas]["flat"]
            au, co = f["by_group"]["autism"], f["by_group"]["control"]
            rows.append([name,
                         f"{au['with_flat']} of {au['n']} ({_pct(au['with_flat'] / au['n'])})",
                         f"{co['with_flat']} of {co['n']} ({_pct(co['with_flat'] / co['n'])})",
                         f"{au['mean_flat']:.2f}", f"{co['mean_flat']:.2f}",
                         f"{_f(f['with']['accuracy'], 2)} (n = {f['with']['n']})",
                         f"{_f(f['without']['accuracy'], 2)} (n = {f['without']['n']})"])
        out += _table(["Atlas", "Autism with flat", "Control with flat", "Mean flat, autism",
                       "Mean flat, control", "Accuracy with flat", "Accuracy without"], rows)

    out += [
        "",
        "## How to read this",
        "",
        "- Differences between sites or quartiles are reported, not tested. With 20 sites and "
        "four atlases some differences are expected by chance alone.",
        "- Site, motion and flat regions are not independent: some sites have more motion and "
        "more flat regions. A difference along one of them can come from another.",
        "- A site whose accuracy is below its own majority baseline is one where predicting the "
        "larger group for everyone would have done as well; this is the clearest sign of where "
        "the models are weakest.",
        "- The frozen-set results are not broken down here, on purpose: the frozen set is "
        "measured once per model (memo 0011), and subgroup views of it would turn into a "
        "second, informal measurement.",
        "",
        "## Limitations this supports in the report",
        "",
        "- Accuracy is uneven across sites, so a single overall accuracy does not describe "
        "every scanner equally well.",
        "- Remaining head motion and flat regions are possible confounds; the models were not "
        "adjusted for them (no site harmonisation or motion regression beyond the ABIDE "
        "preprocessing).",
        "- Leave-site-out evaluation, which tests a model on a site it never saw, is part of "
        "the reliability module planned for FYP-II.",
        "",
    ]
    return "\n".join(out)
