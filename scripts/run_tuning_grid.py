"""Run memo 0011's tuning grid: 12 cross-validation runs per atlas, never the frozen set.

Each configuration is one `train_gnn.py --stage cv` run tagged `--tuning-grid 0011-v1`,
logged to runs/run_log.jsonl with its out-of-fold file. The script is resumable: a
configuration already logged for an atlas is skipped, so if Kaggle stops, run the same
command again and it continues. It never repeats a configuration whose result exists
(memo 0011: every configuration is run once).

Usage (from the repository root):
    python scripts/run_tuning_grid.py --atlas all          # 48 runs
    python scripts/run_tuning_grid.py --atlas rois_cc200   # 12 runs
    python scripts/run_tuning_grid.py --atlas all --dry-run
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from neurographx.m3_model.run_logger import read_runs
from neurographx.m3_model.tuning import ATLAS_KEYS, GRID, GRID_TAG, pending, short

SCRIPT = Path(__file__).with_name("train_gnn.py")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--atlas", default="all", help="an atlas key (rois_cc200) or 'all'")
    p.add_argument("--connectomes", default="data/processed/connectomes")
    p.add_argument("--dry-run", action="store_true", help="list what would run, run nothing")
    args = p.parse_args()
    atlases = ATLAS_KEYS if args.atlas == "all" else (args.atlas,)
    if any(a not in ATLAS_KEYS for a in atlases):
        p.error(f"--atlas must be one of {', '.join(ATLAS_KEYS)} or 'all'")

    todo = [(a, c) for a in atlases for c in pending(read_runs(), short(a))]
    print(f"Grid {GRID_TAG}: {len(GRID)} configurations per atlas; "
          f"{len(todo)} still to run for {', '.join(atlases)}.")
    for i, (atlas, config) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {atlas}: {config.label()}")
        if args.dry_run:
            continue
        started = time.perf_counter()
        cmd = [sys.executable, str(SCRIPT), "--stage", "cv", "--atlas", atlas,
               "--connectomes", args.connectomes, "--tuning-grid", GRID_TAG, *config.args()]
        done = subprocess.run(cmd)
        if done.returncode != 0:
            print(f"Stopped: run {i} failed (exit {done.returncode}). Fix it and run this "
                  "command again; finished configurations are skipped.")
            return done.returncode
        print(f"    done in {time.perf_counter() - started:.0f} s")
    print("All requested configurations are logged." if not args.dry_run else "Dry run only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
