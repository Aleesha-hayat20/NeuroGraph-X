"""Run a reliability grid (memo 0016): one variant run per job, resumable.

The grid definition (configs/reliability/*.yaml) is expanded into a job manifest, written
once to <output>/runs/reliability/<grid name>/manifest.json. Each job is trained and
scored on the development pool and logged to <output>/runs/run_log.jsonl with
"stage": "variant". Run the same command again after a stop: jobs already logged are
skipped.

FYP-I runs this on the synthetic fixture only. Real ABIDE data is refused unless
--allow-real-data is given (the reliability finding is an FYP-II deliverable, memo 0015).

Usage (from the repository root):
    python scripts/run_reliability.py --spec configs/reliability/fixture_grid.yaml \\
        --output /tmp/ngx-reliability
    python scripts/run_reliability.py --spec configs/reliability/fixture_grid.yaml \\
        --output /tmp/ngx-reliability --dry-run
    python scripts/run_reliability.py --spec configs/reliability/fixture_grid.yaml \\
        --output /tmp/ngx-reliability --max-jobs 4
"""
import argparse
import sys
from pathlib import Path

from neurographx.m1_ingestion.splits import LeakageError
from neurographx.m5_reliability.manifest import ManifestError
from neurographx.m5_reliability.runner import OutputRefused, RealDataRefused, run_grid
from neurographx.m5_reliability.variants import SplitError


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", required=True, type=Path, help="grid definition (YAML)")
    p.add_argument("--output", required=True, type=Path,
                   help="folder for the run log, manifest and prediction files "
                        "(outside fixtures/)")
    p.add_argument("--data", choices=["fixtures", "real"], default="fixtures",
                   help="dataset to run on (default: the synthetic fixture)")
    p.add_argument("--allow-real-data", dest="allow_real_data", action="store_true",
                   help="permit --data real (FYP-II)")
    p.add_argument("--max-jobs", dest="max_jobs", type=int,
                   help="stop after this many jobs (the rest stay pending)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="list the pending jobs, train nothing, write nothing")
    args = p.parse_args()
    if args.max_jobs is not None and args.max_jobs < 1:
        p.error("--max-jobs must be 1 or more")
    try:
        run_grid(args.spec, args.output, args.data, allow_real_data=args.allow_real_data,
                 max_jobs=args.max_jobs, dry_run=args.dry_run)
    except (RealDataRefused, OutputRefused, ManifestError, SplitError, LeakageError) as err:
        print(f"Refused: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
