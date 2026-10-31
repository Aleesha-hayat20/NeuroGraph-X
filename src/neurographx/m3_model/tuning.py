"""The declared tuning grid and the selection rule of memo 0011.

Everything a choice depends on is here, written before any tuning result exists:

- GRID: 3 edge densities x class weighting off/on x 2 hidden sizes = 12 configurations
  per atlas, each one 5-fold cross-validation run tagged with GRID_TAG.
- select(): the winner per atlas is the highest mean CV balanced accuracy. Configurations
  within TIE_MARGIN of the best are tied; a tie goes to the fewest changes from the
  baseline (memo 0006), then to the lower standard deviation across folds.

Selection reads the run log only (never the frozen set) and ignores runs logged after
the freeze. Nothing here needs PyTorch.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import product

GRID_TAG = "0011-v1"
ATLAS_KEYS = ("rois_aal", "rois_cc200", "rois_ho", "rois_dosenbach160")
DENSITIES = (0.05, 0.10, 0.20)
CLASS_WEIGHTED = (False, True)
HIDDEN = (32, 64)
BASELINE = {"density": 0.10, "class_weighted": False, "hidden": 64}
TIE_MARGIN = 0.005
# Memo 0011, section 3: runs logged up to Sunday 1 November count. The team works in
# Pakistan time, so the cut-off is midnight PKT; change it only by amending the memo.
FREEZE = "2026-11-02T00:00:00+05:00"


@dataclass(frozen=True)
class Config:
    density: float
    class_weighted: bool
    hidden: int

    def changes(self) -> int:
        """How many settings differ from the memo 0006 baseline."""
        return ((abs(self.density - BASELINE["density"]) > 1e-9)
                + (self.class_weighted != BASELINE["class_weighted"])
                + (self.hidden != BASELINE["hidden"]))

    def label(self) -> str:
        return (f"density {self.density:.2f}, class weights "
                f"{'on' if self.class_weighted else 'off'}, hidden {self.hidden}")

    def args(self) -> list[str]:
        """The command-line arguments that make train_gnn.py run this configuration."""
        out = ["--density", f"{self.density}", "--hidden", str(self.hidden)]
        return out + (["--class-weighted"] if self.class_weighted else [])


GRID = tuple(Config(d, w, h) for d, w, h in product(DENSITIES, CLASS_WEIGHTED, HIDDEN))


def short(atlas_key: str) -> str:
    return atlas_key.removeprefix("rois_")


def config_of(run: dict) -> Config:
    hp, dc = run["hyperparameters"], run["data_config"]
    return Config(round(float(dc["density"]), 4), bool(hp.get("class_weighted", False)),
                  int(hp["hidden"]))


def is_grid_run(run: dict, atlas: str, tag: str = GRID_TAG) -> bool:
    return (run.get("dataset") == "ABIDE" and run.get("stage") == "cv"
            and run.get("atlas") == atlas
            and (run.get("data_config") or {}).get("tuning_grid") == tag)


def grid_runs(runs: list[dict], atlas: str, tag: str = GRID_TAG) -> dict[Config, list[dict]]:
    """Every tagged CV run of `atlas`, grouped by configuration, in log order."""
    out: dict[Config, list[dict]] = {}
    for run in runs:
        if is_grid_run(run, atlas, tag):
            out.setdefault(config_of(run), []).append(run)
    return out


def pending(runs: list[dict], atlas: str, tag: str = GRID_TAG) -> list[Config]:
    """Grid configurations of `atlas` with no tagged run yet, in grid order (resumable)."""
    done = grid_runs(runs, atlas, tag)
    return [c for c in GRID if c not in done]


def _when(run: dict) -> datetime:
    return datetime.fromisoformat(run["timestamp"])


@dataclass
class Row:
    config: Config
    run: dict | None            # the run that counts for selection
    ignored: list[dict]         # later duplicates, or runs after the freeze
    note: str = ""

    @property
    def balanced(self) -> float | None:
        return self.run["metrics"]["cv_balanced_accuracy"]["mean"] if self.run else None

    @property
    def balanced_sd(self) -> float | None:
        return self.run["metrics"]["cv_balanced_accuracy"]["sd"] if self.run else None


def table(runs: list[dict], atlas: str, freeze: str = FREEZE, tag: str = GRID_TAG) -> list[Row]:
    """One row per grid configuration: the run that counts and the runs that do not.

    A configuration counts once (memo 0011: every configuration is run once): its first
    run logged before the freeze. Later runs of it, and any run after the freeze, are
    listed as ignored so the report shows them.
    """
    cutoff = datetime.fromisoformat(freeze)
    grouped = grid_runs(runs, atlas, tag)
    rows = []
    for config in GRID:
        found = sorted(grouped.get(config, []), key=_when)
        before = [r for r in found if _when(r) < cutoff]
        after = [r for r in found if _when(r) >= cutoff]
        if before:
            note = f"{len(before) - 1} later duplicate(s) ignored" if len(before) > 1 else ""
            if after:
                late = f"{len(after)} run(s) after the freeze ignored"
                note = "; ".join(filter(None, [note, late]))
            rows.append(Row(config, before[0], before[1:] + after, note))
        else:
            note = "not run before the freeze" + (" (a later run is ignored)" if after else "")
            rows.append(Row(config, None, after, note))
    return rows


def select(rows: list[Row]) -> tuple[Row | None, list[Row]]:
    """The winner and the tied set, by memo 0011 section 2. (None, []) if nothing ran."""
    scored = [r for r in rows if r.run is not None and r.balanced is not None]
    if not scored:
        return None, []
    best = max(r.balanced for r in scored)
    tied = [r for r in scored if r.balanced >= best - TIE_MARGIN - 1e-12]
    grid_order = {c: i for i, c in enumerate(GRID)}
    winner = min(tied, key=lambda r: (r.config.changes(), r.balanced_sd or 0.0,
                                      -r.balanced, grid_order[r.config]))
    return winner, tied


def _fmt(value, digits=4) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def _final_step(atlas: str, winner: Row) -> str:
    """Memo 0011, section 4: what happens to the frozen set for this atlas."""
    command = (f"`python scripts/train_gnn.py --stage final --atlas rois_{atlas} "
               f"--epochs-from-cv {winner.run['run_id']}")
    if atlas != "cc200":
        return f"Final model, frozen set measured once: {command}`"
    if winner.config.changes() == 0:
        return ("CC200: the baseline configuration was selected, so there is no second frozen "
                "measurement; run `00252f2b` remains the final CC200 model.")
    return (f"CC200: a configuration other than the baseline was selected, so it is measured "
            f"once more as a declared repeat: {command} --allow-repeat` "
            "(reason: post-tuning measurement per memo 0011).")


def render(results: dict[str, tuple[list[Row], Row | None, list[Row]]], freeze: str = FREEZE,
           tag: str = GRID_TAG) -> str:
    """docs/reports/tuning_selection.md: every configuration per atlas, the winner marked."""
    lines = [
        "# Tuning selection (memo 0011)",
        "",
        f"Grid `{tag}`: edge density {', '.join(f'{d:.2f}' for d in DENSITIES)}; class-weighted "
        f"loss off/on; hidden {', '.join(map(str, HIDDEN))}. 12 configurations per atlas, each "
        "one 5-fold cross-validation run on the 761 development participants.",
        "",
        f"Rule: highest mean CV balanced accuracy; within {TIE_MARGIN} of the best counts as "
        "tied, then fewest changes from the baseline (density 0.10, class weights off, hidden "
        "64), then lower standard deviation across folds.",
        f"Runs logged before the freeze ({freeze}) count; the frozen set is not read.",
        "",
        "**The selected configuration's CV score is optimistic: it won a contest of twelve. It "
        "is reported next to the frozen-set result, never instead of it.**",
        "",
    ]
    for atlas, (rows, winner, tied) in results.items():
        lines += [f"## {atlas}", ""]
        lines += ["| Density | Class weights | Hidden | Changes | Run | CV balanced (SD) | "
                  "CV accuracy | CV AUC | Epochs | Selected | Note |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        tied_ids = {id(r) for r in tied}
        for r in rows:
            m = r.run["metrics"] if r.run else {}
            mark = "**selected**" if r is winner else ("tied" if id(r) in tied_ids else "")
            lines.append(
                f"| {r.config.density:.2f} | {'on' if r.config.class_weighted else 'off'} | "
                f"{r.config.hidden} | {r.config.changes()} | "
                f"{('`' + r.run['run_id'] + '`') if r.run else ''} | "
                f"{_fmt(r.balanced)}{(' (' + _fmt(r.balanced_sd) + ')') if r.run else ''} | "
                f"{_fmt(m.get('cv_accuracy', {}).get('mean')) if m else ''} | "
                f"{_fmt(m.get('cv_auc', {}).get('mean')) if m else ''} | "
                f"{m.get('chosen_epochs', '') if m else ''} | {mark} | {r.note} |")
        ran = sum(r.run is not None for r in rows)
        lines.append("")
        if winner is None:
            lines += [f"No configuration of {atlas} was run before the freeze; "
                      "nothing selected.", ""]
            continue
        lines += [
            f"{ran} of 12 configurations ran before the freeze. "
            f"Selected: **{winner.config.label()}**, "
            f"CV run `{winner.run['run_id']}` (balanced accuracy {_fmt(winner.balanced)}, "
            f"{len(tied)} configuration(s) within {TIE_MARGIN}).",
            "",
            _final_step(atlas, winner),
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"
