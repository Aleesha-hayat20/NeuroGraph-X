#!/usr/bin/env python3
"""Step 2 of Week 1: build the metadata report.

Usage:
    python scripts/02_metadata_report.py

Writes docs/reports/metadata_report.md and charts into docs/reports/figures/.
Run 01_fetch_phenotypic.py first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from neurographx.config import load  # noqa: E402
from neurographx.m1_ingestion import metadata as md  # noqa: E402
from neurographx.utils.paths import resolve  # noqa: E402

INK, STROKE, ACCENT = "#1F2933", "#5B6B7A", "#B08D3F"
plt.rcParams.update(
    {"font.size": 9, "text.color": INK, "axes.labelcolor": INK,
     "xtick.color": STROKE, "ytick.color": STROKE, "axes.edgecolor": "#C3CBD3",
     "figure.dpi": 200, "savefig.dpi": 200}
)


def _table(df) -> str:
    if df is None or len(df) == 0:
        return "_Not available in this file._\n"
    return df.to_markdown(index=False) + "\n"


def _bar(series, title, xlabel, path: Path, horizontal=False, color=STROKE):
    fig, ax = plt.subplots(figsize=(7.4, max(2.4, 0.28 * len(series) + 1.2)) if horizontal
                           else (7.4, 3.2))
    if horizontal:
        ax.barh(series.index.astype(str)[::-1], series.values[::-1], color=color,
                edgecolor="#FFFFFF", height=0.72)
        ax.set_xlabel(xlabel)
    else:
        ax.bar(series.index.astype(str), series.values, color=color, edgecolor="#FFFFFF")
        ax.set_ylabel(xlabel)
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold", pad=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x" if horizontal else "y", color="#EDF0F3", lw=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def build(csv_path: Path, out_md: Path, fig_dir: Path, motion_column: str | None = None) -> str:
    df = md.load_phenotypic(csv_path)
    today = dt.date.today().isoformat()
    figures = []

    if "SITE_ID" in df.columns:
        s = df["SITE_ID"].value_counts()
        _bar(s, "Participants by imaging site", "participants",
             fig_dir / "site_counts.png", horizontal=True)
        figures.append(("Participants by imaging site", "figures/site_counts.png"))

    if "DX_GROUP" in df.columns:
        s = df["DX_GROUP"].value_counts().sort_index()
        s.index = [md.DX_LABELS.get(i, str(i)) for i in s.index]
        _bar(s, "Participants by diagnostic group", "participants",
             fig_dir / "group_counts.png")
        figures.append(("Participants by diagnostic group", "figures/group_counts.png"))

    if "AGE_AT_SCAN" in df.columns:
        fig, ax = plt.subplots(figsize=(7.4, 3.2))
        ax.hist(df["AGE_AT_SCAN"].dropna(), bins=30, color=STROKE, edgecolor="#FFFFFF")
        ax.set_xlabel("age at scan, years")
        ax.set_ylabel("participants")
        ax.set_title("Age distribution", loc="left", fontsize=10.5, fontweight="bold", pad=10)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color="#EDF0F3", lw=0.8)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(fig_dir / "age_hist.png", bbox_inches="tight")
        plt.close(fig)
        figures.append(("Age distribution", "figures/age_hist.png"))

    col = md.pick_motion_column(df, motion_column)
    if col:
        fig, ax = plt.subplots(figsize=(7.4, 3.2))
        ax.hist(df[col].dropna(), bins=40, color=ACCENT, edgecolor="#FFFFFF")
        ax.set_xlabel(col)
        ax.set_ylabel("participants")
        ax.set_title(f"Distribution of {col}", loc="left", fontsize=10.5,
                     fontweight="bold", pad=10)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color="#EDF0F3", lw=0.8)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(fig_dir / "motion_hist.png", bbox_inches="tight")
        plt.close(fig)
        figures.append((f"Distribution of {col}", "figures/motion_hist.png"))

    rater = md.would_pass_all_raters(df)

    parts = [
        "# ABIDE Preprocessed: Metadata Report",
        "",
        f"**Generated:** {today}  ",
        f"**Source file:** `{csv_path.name}`  ",
        f"**Rows:** {len(df)}  **Columns:** {len(df.columns)}",
        "",
        "This report describes the cohort as distributed. No quality control has been",
        "applied to the counts below unless a section says otherwise.",
        "",
        "## 1. Diagnostic group",
        "",
        _table(md._counts(df, "DX_GROUP", md.DX_LABELS)),
        "## 2. Imaging site",
        "",
        _table(md._counts(df, "SITE_ID")),
        "## 3. Sex",
        "",
        _table(md._counts(df, "SEX", md.SEX_LABELS)),
        "## 4. Age bands",
        "",
        _table(md.age_bands(df)),
        "## 5. Site by diagnostic group",
        "",
        "This table drives the stratification of the frozen evaluation set.",
        "",
        _table(md.site_by_group(df)),
        "## 6. Quality control variables",
        "",
        "Accepted values follow `nilearn.datasets.fetch_abide_pcp(quality_checked=True)`,",
        "version 0.14.1.",
        "",
        _table(md.qc_summary(df)),
    ]

    if rater.get("applicable"):
        parts += [
            f"Applying the standard rater filter to the {len(rater['columns_used'])} rater "
            f"columns present would retain **{rater['passing_all']} of {rater['total']}** "
            "participants.",
            "",
        ]
    else:
        parts += ["_No rater columns matching the expected names were found._", ""]

    parts += [
        "## 7. Head motion and related variables",
        "",
        "Columns discovered by pattern rather than assumed. Confirm the intended one",
        "before setting a threshold.",
        "",
        _table(md.motion_summary(df)),
        "## 8. All column names",
        "",
        "```",
        "\n".join(f"{i:3d}. {c}" for i, c in enumerate(df.columns, 1)),
        "```",
        "",
    ]

    if figures:
        parts += ["## 9. Figures", ""]
        for title, rel in figures:
            parts += [f"**{title}**", "", f"![{title}]({rel})", ""]

    text = "\n".join(parts)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=None, help="path to the phenotypic CSV")
    args = ap.parse_args()

    cfg = load("data.yaml")
    csv_path = args.csv or (resolve(cfg["paths"]["raw"]) / cfg["dataset"]["phenotypic_file"])
    if not csv_path.exists():
        print(f"Phenotypic file not found: {csv_path}")
        print("Run scripts/01_fetch_phenotypic.py first.")
        return 1

    reports = resolve(cfg["paths"]["reports"])
    motion_column = load("qc_criteria.yaml").get("motion", {}).get("column")
    build(csv_path, reports / "metadata_report.md", reports / "figures", motion_column)
    print(f"Wrote {reports / 'metadata_report.md'}")
    print(f"Figures in {reports / 'figures'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
