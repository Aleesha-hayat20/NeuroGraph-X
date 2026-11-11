"""Confound check on the out-of-fold predictions: site, head motion, flat regions.

Writes docs/reports/confound_check.md, a limitation analysis for the report (work plan,
Week 6). The method is described in src/neurographx/m3_model/confounds.py. Reads the run
log, the registry, the out-of-fold files, the QC cohort, the development folds and the
connectome store; reads no frozen-set file and fits nothing.

Usage (from the repository root):
    python scripts/confound_check.py                    # real data -> docs/reports/
    python scripts/confound_check.py --data fixtures    # fixture data, printed only
    python scripts/confound_check.py --out other.md     # write somewhere else
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from neurographx import datasource
from neurographx.m3_model.confounds import ConfoundInputError, analyse, render

REPORT = Path("docs/reports/confound_check.md")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", choices=datasource.MODES, default=None,
                    help="which dataset (default: NGX_DATA, or real when unset)")
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write the report (default: docs/reports/confound_check.md "
                         "for the real data; fixture results are only printed)")
    args = ap.parse_args(argv)

    mode = args.data or datasource.mode()
    root = datasource.data_root(mode)
    try:
        result = analyse(root)
    except ConfoundInputError as err:
        print(f"Confound check stopped: {err}")
        return 1
    source = "the real data" if mode == "real" else "the SYNTHETIC fixture data"
    text = render(result, date.today().isoformat(), source)

    out = args.out or (root / REPORT if mode == "real" else None)
    if out is None:
        print(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
    for atlas, a in result["atlases"].items():
        o = a["overall"]
        print(f"  {atlas:<13} n={o['n']}  OOF accuracy {o['accuracy']:.4f}  "
              f"balanced {o['balanced_accuracy']:.4f}")
    print(f"  {len(result['sites'])} sites, 4 motion quartiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
