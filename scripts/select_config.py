"""Choose one configuration per atlas from the tuning runs (memo 0011, section 2).

Reads runs/run_log.jsonl only: the frozen set is not read. Writes
docs/reports/tuning_selection.md with all 12 configurations per atlas and the winner
marked, and prints the final-stage command for each atlas.

Usage (from the repository root, on Monday 2 November, after the freeze):
    python scripts/select_config.py
"""
import argparse
from pathlib import Path

from neurographx.m3_model.run_logger import read_runs
from neurographx.m3_model.tuning import ATLAS_KEYS, FREEZE, GRID_TAG, render, select, short, table

REPORT = Path("docs/reports/tuning_selection.md")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--freeze", default=FREEZE, help="runs logged at or after this are ignored")
    p.add_argument("--out", default=str(REPORT))
    args = p.parse_args()

    runs = read_runs()
    results = {}
    for key in ATLAS_KEYS:
        rows = table(runs, short(key), args.freeze, GRID_TAG)
        winner, tied = select(rows)
        results[short(key)] = (rows, winner, tied)
        ran = sum(r.run is not None for r in rows)
        chosen = f"{winner.config.label()} (run {winner.run['run_id']})" if winner else "nothing"
        print(f"{short(key):>13}: {ran}/12 configurations; selected {chosen}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(results, args.freeze, GRID_TAG), encoding="utf-8", newline="\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
