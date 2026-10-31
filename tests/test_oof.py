"""Out-of-fold predictions from cross-validation (Week 4, input to calibration, memo 0010).

The unit tests need no PyTorch. The last test runs the real training script's `cv`
stage on the fixture dataset (memo 0014) in a temporary folder, so it never touches
the repository's run log; it is skipped where PyTorch is not installed.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from neurographx.m3_model.oof import (
    COLUMNS,
    check_oof,
    fold_rows,
    oof_path,
    read_oof,
    write_oof,
)
from neurographx.utils.paths import project_root

ROOT = project_root()
FX = ROOT / "fixtures"


def _dev(n=6):
    return pd.DataFrame({"SUB_ID": range(50001, 50001 + n),
                         "FILE_ID": [f"Site_{50001 + i:07d}" for i in range(n)],
                         "SITE_ID": ["S1", "S2"] * (n // 2),
                         "DX_GROUP": [1, 2] * (n // 2),
                         "fold": [0, 1, 2] * (n // 3)})


def _oof(dev):
    parts = [fold_rows(dev[dev.fold == k], k, (dev[dev.fold == k].DX_GROUP == 1).astype(int),
                       np.linspace(0.2, 0.8, int((dev.fold == k).sum())))
             for k in sorted(dev.fold.unique())]
    return pd.concat(parts, ignore_index=True)


def test_fold_rows_has_the_columns_and_a_prediction_from_the_probability():
    dev = _dev()
    rows = fold_rows(dev.iloc[:2], 0, [1, 0], [0.7, 0.3])
    assert tuple(rows.columns) == COLUMNS
    assert rows.prediction.tolist() == [1, 0]
    assert rows.fold.tolist() == [0, 0]


def test_fold_rows_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        fold_rows(_dev().iloc[:2], 0, [1], [0.5, 0.5])


def test_valid_oof_covers_the_development_pool_once():
    dev = _dev()
    check_oof(_oof(dev), dev)


@pytest.mark.parametrize("breakage", ["duplicate", "missing", "out_of_range", "nan"])
def test_invalid_oof_is_rejected(breakage):
    dev = _dev()
    oof = _oof(dev)
    if breakage == "duplicate":
        oof = pd.concat([oof, oof.iloc[[0]]], ignore_index=True)
    elif breakage == "missing":
        oof = oof.iloc[1:]
    elif breakage == "out_of_range":
        oof.loc[0, "prob_autism"] = 1.2
    else:
        oof.loc[0, "prob_autism"] = np.nan
    with pytest.raises(ValueError):
        check_oof(oof, dev)


def test_frozen_participant_in_oof_is_rejected():
    dev = _dev()
    frozen = dev.iloc[[0]][["SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP"]]
    with pytest.raises(ValueError, match="frozen"):
        check_oof(_oof(dev), dev, frozen)


def test_write_sorts_by_participant_and_returns_the_file_hash(tmp_path):
    import hashlib

    dev = _dev()
    path = oof_path("cc200", "abcd1234", tmp_path)
    sha = write_oof(_oof(dev).iloc[::-1], path, dev)
    assert path.name == "cc200_abcd1234_oof.csv"
    assert sha == hashlib.sha256(path.read_bytes()).hexdigest()
    back = read_oof(path)
    assert back.SUB_ID.tolist() == sorted(dev.SUB_ID)
    assert back.FILE_ID.tolist() == sorted(dev.FILE_ID)


def test_cv_stage_writes_oof_for_every_development_participant(tmp_path):
    """The real `cv` stage, on the fixture dataset, in a scratch folder."""
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    (tmp_path / "data" / "splits").mkdir(parents=True)
    (tmp_path / "data" / "frozen").mkdir(parents=True)
    shutil.copy(FX / "data/splits/cv5_folds.csv", tmp_path / "data/splits/cv5_folds.csv")
    # the script reads the frozen file by its real name; the fixture's has 6 rows
    shutil.copy(FX / "data/frozen/frozen_eval_6.csv",
                tmp_path / "data/frozen/frozen_eval_100.csv")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    env.pop("NGX_DATA", None)
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts/train_gnn.py"), "--stage", "cv",
         "--connectomes", str(FX / "data/processed/connectomes"),
         "--epochs", "3", "--hidden", "8", "--layers", "2", "--batch-size", "4"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]

    runs = [json.loads(line) for line in (tmp_path / "runs/run_log.jsonl").read_text()
            .splitlines()]
    assert len(runs) == 1 and runs[0]["stage"] == "cv"
    meta = runs[0]["metrics"]["oof"]
    oof_file = tmp_path / meta["file"]
    assert oof_file.exists()
    import hashlib
    assert meta["sha256"] == hashlib.sha256(oof_file.read_bytes()).hexdigest()

    dev = pd.read_csv(FX / "data/splits/cv5_folds.csv")
    frozen = pd.read_csv(FX / "data/frozen/frozen_eval_6.csv")
    oof = read_oof(oof_file)
    check_oof(oof, dev, frozen)
    assert meta["n"] == len(dev) == len(oof)
    # each participant's OOF fold is the fold it was held out in
    merged = oof.merge(dev[["SUB_ID", "fold"]], on="SUB_ID", suffixes=("", "_split"))
    assert (merged.fold == merged.fold_split).all()
    assert runs[0]["metrics"]["cv_seconds"] >= 0
    assert not (tmp_path / "checkpoints").exists()  # cross-validation saves no model
