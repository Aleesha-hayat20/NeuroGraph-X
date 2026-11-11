"""Check that the run log, registry, checkpoints, data files and analysis log agree.

Run before every demonstration on the real data, and in CI on the fixture dataset
(work plan, Week 6). The checks are described in src/neurographx/integrity.py.

Usage (from the repository root):
    python scripts/check_integrity.py                  # the real data
    python scripts/check_integrity.py --data fixtures  # the fixture dataset (memo 0014)
    python scripts/check_integrity.py --quiet          # only warnings, failures, summary
    python scripts/check_integrity.py --no-replay      # skip re-running the models

Exit status: 0 when nothing failed, 1 otherwise (warnings do not fail the check).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neurographx import datasource
from neurographx.integrity import check


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", choices=datasource.MODES, default=None,
                    help="which dataset (default: NGX_DATA, or real when unset)")
    ap.add_argument("--root", type=Path, default=None,
                    help="check the dataset in this folder instead (used by the tests)")
    ap.add_argument("--quiet", action="store_true",
                    help="print only warnings, failures and the summary")
    ap.add_argument("--no-replay", action="store_true",
                    help="do not re-run the registered models (faster; weaker)")
    args = ap.parse_args(argv)

    mode = args.data or datasource.mode()
    report = check(args.root, mode, replay=not args.no_replay)
    print("\n".join(report.lines(verbose=not args.quiet)))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
