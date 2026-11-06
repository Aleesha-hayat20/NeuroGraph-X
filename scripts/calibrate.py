"""Fit the confidence calibrator of a final model (memo 0010) and score it.

For each final run given:
  1. finds its cross-validation run (metrics.cv_run_id) and that run's OOF table
     (metrics.oof), and checks the file's SHA-256 against the run log;
  2. checks the OOF table covers the development pool once each and holds no frozen
     participant (oof.check_oof);
  3. fits Platt scaling on all OOF rows, and scores it cross-fitted on OOF;
  4. scores the frozen set before and after from the final run's saved frozen
     predictions (metrics.frozen.predictions, hash checked). Nothing is fitted or chosen
     on them, and the model is not run again: this is not a second measurement;
  5. writes runs/calibration/<atlas>_<run_id>.json and the reliability diagram
     docs/reports/figures/calibration_<atlas>_<run_id>.png.

Reads only files; needs no GPU and no connectomes.

Usage (from the repository root):
    python scripts/calibrate.py --run 1a2b3c4d
    python scripts/calibrate.py --run 1a2b3c4d 5e6f7a8b ...
"""
import argparse
import hashlib
from pathlib import Path

import pandas as pd

from neurographx.m3_model.calibration import (
    calibrate,
    calibration_path,
    reliability_figure,
    write_calibration,
)
from neurographx.m3_model.oof import check_oof, read_oof
from neurographx.m3_model.run_logger import LOG_PATH, get_run

FIGURES = Path("docs/reports/figures")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _checked(meta: dict, what: str) -> Path:
    path = Path(meta["file"])
    if not path.exists():
        raise SystemExit(f"{what} file not found: {path}")
    if _sha256(path) != meta["sha256"]:
        raise SystemExit(f"{what} file {path} does not match the SHA-256 in the run log")
    return path


def calibrate_run(run_id: str, log_path: Path = LOG_PATH, out_dir: Path | None = None,
                  figures: Path = FIGURES) -> dict:
    final = get_run(run_id, log_path)
    if final is None or final.get("stage") != "final":
        raise SystemExit(f"{run_id} is not a final run in {log_path}")
    atlas = final["atlas"]
    cv_id = final["metrics"].get("cv_run_id")
    cv = get_run(cv_id, log_path) if cv_id else None
    if cv is None or cv.get("stage") != "cv":
        raise SystemExit(f"final run {run_id}: its cross-validation run {cv_id} is not in the log")
    if "oof" not in cv["metrics"]:
        raise SystemExit(f"CV run {cv_id} predates OOF files (Week 4); it cannot be calibrated "
                         "(memo 0010, section 3)")

    dc = final["data_config"]
    folds_file, frozen_file = Path(dc["folds_file"]), Path(dc["frozen_file"])
    for path, key in ((folds_file, "folds_sha256"), (frozen_file, "frozen_sha256")):
        if _sha256(path) != dc[key]:
            raise SystemExit(f"{path} differs from the file run {run_id} trained with")
    development, frozen = pd.read_csv(folds_file), pd.read_csv(frozen_file)

    oof_file = _checked(cv["metrics"]["oof"], "OOF")
    oof = read_oof(oof_file)
    check_oof(oof, development, frozen)

    pred_meta = final["metrics"]["frozen"].get("predictions")
    frozen_preds = read_oof(_checked(pred_meta, "Frozen predictions")) if pred_meta else None

    record = {"atlas": atlas, "run_id": run_id, "cv_run_id": cv_id,
              "oof_file": oof_file.as_posix(), "oof_sha256": cv["metrics"]["oof"]["sha256"],
              **calibrate(oof, frozen_preds)}
    out = calibration_path(atlas, run_id) if out_dir is None else Path(out_dir) / \
        f"{atlas}_{run_id}.json"
    write_calibration(record, out)
    figure = Path(figures) / f"calibration_{atlas}_{run_id}.png"
    reliability_figure(record, figure, f"{atlas.upper()}, final run {run_id}: reliability")

    o = record["oof"]
    print(f"{atlas} {run_id} (CV {cv_id}): a = {record['a']}, b = {record['b']}, n = {record['n']}")
    print(f"  OOF    ECE {o['before']['ece']} -> {o['after_cross_fitted']['ece']} (cross-fitted), "
          f"Brier {o['before']['brier']} -> {o['after_cross_fitted']['brier']}")
    if record["frozen"]:
        f = record["frozen"]
        print(f"  Frozen ECE {f['before']['ece']} -> {f['after']['ece']}, "
              f"Brier {f['before']['brier']} -> {f['after']['brier']}, "
              f"accuracy {f['accuracy_before']} -> {f['accuracy_after']} "
              f"({f['prediction_flips']} prediction(s) flipped at 0.5)")
    else:
        print("  Frozen: no saved frozen predictions for this run (logged before Week 5)")
    print(f"  Wrote {out} and {figure}")
    return record


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", nargs="+", required=True, help="final run_id(s) to calibrate")
    args = p.parse_args()
    for run_id in args.run:
        try:
            calibrate_run(run_id)
        except (FileExistsError, ValueError) as err:
            raise SystemExit(f"{run_id}: {err}") from None


if __name__ == "__main__":
    main()
