"""Bring a Kaggle results zip into the repository, checking it on the way (Week 6, #98).

The Week 6 notebook ends with w6_results.zip:

    run_log.jsonl                      the whole run log after the run
    model_registry.json                the registry after the run
    checkpoints/<atlas>_<run_id>.pt    the final models
    runs/frozen_predictions/*.csv      per-participant frozen predictions
    runs/calibration/*.json            calibrators (memo 0010)
    figures/calibration_*.png          reliability diagrams

This script refuses to import unless:
  - the zip's run log starts with every line of the repository's run log, unchanged
    (the log only ever grows at the end);
  - every new run's checkpoint, frozen predictions and calibration file match the
    SHA-256 values recorded for them (either line ending for text files);
  - the registry serves only runs that are in the run log.
Then it copies the files into place and prints what changed. It never deletes anything;
review with `git status` and `git diff --stat` before committing.

Usage (from the repository root):
    python scripts/import_results.py ~/Downloads/w6_results.zip
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

LOG, REGISTRY = Path("runs/run_log.jsonl"), Path("runs/model_registry.json")
COPY = (("checkpoints", Path("checkpoints"), "*.pt"),
        ("runs/frozen_predictions", Path("runs/frozen_predictions"), "*.csv"),
        ("runs/calibration", Path("runs/calibration"), "*.json"),
        ("figures", Path("docs/reports/figures"), "*.png"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches(path: Path, logged: str, text: bool) -> bool:
    data = path.read_bytes()
    if not text:
        return _sha(data) == logged
    lf = data.replace(b"\r\n", b"\n")
    return logged in {_sha(data), _sha(lf), _sha(lf.replace(b"\n", b"\r\n"))}


def check_and_import(zip_path: Path, repo: Path = Path(".")) -> list[dict]:
    """Return the new runs after copying; raise SystemExit with a reason if anything is off."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        new_log, old_log = tmp / "run_log.jsonl", repo / LOG
        if not new_log.exists():
            raise SystemExit(f"{zip_path} has no run_log.jsonl: is it the results zip?")
        old_lines = [x for x in old_log.read_text(encoding="utf-8").splitlines() if x.strip()]
        new_lines = [x for x in new_log.read_text(encoding="utf-8").splitlines() if x.strip()]
        if new_lines[:len(old_lines)] != old_lines:
            raise SystemExit("the zip's run log does not start with the repository's run log "
                             "unchanged: refusing (the log is append-only)")
        added = [json.loads(x) for x in new_lines[len(old_lines):]]
        if not added:
            raise SystemExit("the zip's run log has no new runs")

        for run in added:
            rid, atlas = run["run_id"], run["atlas"]
            if run.get("stage") == "final":
                ckpt = tmp / "checkpoints" / Path(run["checkpoint_path"]).name
                if not ckpt.exists() or not _matches(ckpt, run["checkpoint_sha256"], False):
                    raise SystemExit(f"{atlas} {rid}: checkpoint missing or its SHA-256 differs")
                pred = run["metrics"]["frozen"].get("predictions")
                if pred:
                    f = tmp / "runs/frozen_predictions" / Path(pred["file"]).name
                    if not f.exists() or not _matches(f, pred["sha256"], True):
                        raise SystemExit(f"{atlas} {rid}: frozen predictions missing or differ")
                cal = tmp / "runs/calibration" / f"{atlas}_{rid}.json"
                if cal.exists():
                    record = json.loads(cal.read_text(encoding="utf-8"))
                    if record.get("run_id") != rid:
                        raise SystemExit(f"{cal.name} names run {record.get('run_id')}, not {rid}")

        all_ids = {json.loads(x)["run_id"] for x in new_lines}
        registry = json.loads((tmp / "model_registry.json").read_text(encoding="utf-8"))
        for atlas, entry in registry.items():
            if entry["run_id"] not in all_ids:
                raise SystemExit(f"registry serves {atlas} run {entry['run_id']}, not in the log")

        shutil.copyfile(new_log, repo / LOG)
        shutil.copyfile(tmp / "model_registry.json", repo / REGISTRY)
        for src, dst, pattern in COPY:
            (repo / dst).mkdir(parents=True, exist_ok=True)
            for f in sorted((tmp / src).glob(pattern)):
                shutil.copyfile(f, repo / dst / f.name)
    return added


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("zip", type=Path, help="the results zip downloaded from Kaggle")
    args = p.parse_args()
    added = check_and_import(args.zip)
    print(f"Imported {len(added)} new run(s); every hash checked:")
    for run in added:
        f = run["metrics"].get("frozen", {})
        extra = (f" frozen acc {f.get('accuracy')}, balanced {f.get('balanced_accuracy')}, "
                 f"AUC {f.get('auc')}" if f else "")
        print(f"  {run['run_id']} {run['atlas']:>12} {run.get('stage', '-'):>6}{extra}")
    print("Next: git status, then git add runs docs/reports/figures (checkpoints only if "
          "memo 0009 option A is confirmed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
