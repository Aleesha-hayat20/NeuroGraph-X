"""Tests for confidence calibration (memo 0010).

The unit tests need no PyTorch. The end-to-end test trains a tiny model on the fixture
dataset (cv, then final), calibrates it with the real script, and checks the files.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from neurographx.m3_model.calibration import (
    apply_platt,
    brier,
    calibrate,
    cross_fitted,
    ece,
    fit_platt,
    read_calibration,
    reliability_table,
    write_calibration,
)
from neurographx.utils.paths import project_root

ROOT = project_root()
FX = ROOT / "fixtures"


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def _synthetic(n, a_true, b_true, seed=0):
    """Raw probabilities p and labels drawn so that the true calibration map is (a, b)."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0, 1.5, n)
    p = _sigmoid(z)
    y = (rng.random(n) < _sigmoid(a_true * z + b_true)).astype(int)
    return p, y


def _oof(p, y, n_folds=5):
    return pd.DataFrame({"SUB_ID": np.arange(len(p)), "fold": np.arange(len(p)) % n_folds,
                         "label": y, "prob_autism": p, "prediction": (p >= 0.5).astype(int)})


# ---------------------------------------------------------------------------
# The calibrator
# ---------------------------------------------------------------------------

def test_fit_recovers_a_known_calibration_map():
    p, y = _synthetic(20000, a_true=0.5, b_true=-0.4)  # over-confident, leans to autism
    a, b = fit_platt(p, y)
    assert abs(a - 0.5) < 0.05 and abs(b + 0.4) < 0.05


def test_fit_converges_for_a_very_overconfident_model():
    """Real OOF tables need a around 0.1 to 0.3: plain Newton from a = 1 diverges there."""
    rng = np.random.default_rng(7)
    z = rng.normal(0, 8, 800)  # raw probabilities pushed to 0 and 1
    y = (rng.random(800) < _sigmoid(0.1 * z - 0.05)).astype(int)
    a, b = fit_platt(_sigmoid(z), y)
    assert np.isfinite([a, b]).all()
    assert 0.05 < a < 0.2 and abs(b) < 0.3
    q = apply_platt(_sigmoid(z), a, b)
    assert ece(q, y) < ece(_sigmoid(z), y)


def test_already_calibrated_probabilities_give_the_identity():
    p, y = _synthetic(20000, a_true=1.0, b_true=0.0, seed=1)
    a, b = fit_platt(p, y)
    assert abs(a - 1) < 0.05 and abs(b) < 0.05


def test_calibration_keeps_the_order_of_participants():
    """So accuracy-free measures such as AUC are unchanged (memo 0010, rationale)."""
    p, y = _synthetic(500, 0.6, 0.3, seed=2)
    a, b = fit_platt(p, y)
    assert a > 0
    q = apply_platt(p, a, b)
    assert (np.argsort(p, kind="stable") == np.argsort(q, kind="stable")).all()


@pytest.mark.parametrize("label, message", [([1, 1, 1, 1], "both classes"),
                                            ([0, 1, 2, 1], "0 \\(control\\) or 1")])
def test_bad_fitting_data_is_rejected(label, message):
    with pytest.raises(ValueError, match=message):
        fit_platt([0.2, 0.4, 0.6, 0.8], label)


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------

def test_ece_and_brier_on_hand_worked_examples():
    # all at 0.7, and 7 of 10 are autism: perfectly calibrated
    assert ece([0.7] * 10, [1] * 7 + [0] * 3) == pytest.approx(0.0)
    # all at 0.9, but only half are autism: gap 0.4
    assert ece([0.9] * 10, [1] * 5 + [0] * 5) == pytest.approx(0.4)
    assert brier([1.0, 0.0, 0.5], [1, 0, 1]) == pytest.approx(0.25 / 3)


def test_reliability_table_uses_ten_equal_bins_and_counts_everyone():
    prob = [0.0, 0.05, 0.1, 0.55, 0.99, 1.0]
    rows = reliability_table(prob, [0, 0, 1, 1, 1, 1])
    assert [r["lower"] for r in rows] == [0.0, 0.1, 0.5, 0.9]  # p = 1.0 is in the last bin
    assert sum(r["n"] for r in rows) == len(prob)


def test_calibration_lowers_the_cross_fitted_error_of_an_overconfident_model():
    p, y = _synthetic(2000, a_true=0.4, b_true=0.0, seed=3)
    oof = _oof(p, y)
    after = cross_fitted(oof)
    assert ece(after, y) < ece(p, y)
    assert brier(after, y) < brier(p, y)


def test_cross_fitting_never_scores_a_row_with_a_calibrator_fitted_on_it():
    p, y = _synthetic(500, 0.5, 0.2, seed=4)
    oof = _oof(p, y)
    after = cross_fitted(oof)
    held = oof.fold.to_numpy() == 2
    a, b = fit_platt(p[~held], y[~held])  # fitted on the other four folds only
    assert np.allclose(after[held], apply_platt(p[held], a, b))


def test_calibrate_reports_oof_and_frozen_before_and_after():
    p, y = _synthetic(800, 0.5, -0.3, seed=5)
    fp, fy = _synthetic(100, 0.5, -0.3, seed=6)
    frozen = pd.DataFrame({"label": fy, "prob_autism": fp})
    record = calibrate(_oof(p, y), frozen)
    assert record["method"] == "platt" and record["n"] == 800
    assert set(record["oof"]) >= {"before", "after_cross_fitted"}
    f = record["frozen"]
    assert f["n"] == 100
    q = apply_platt(fp, record["a"], record["b"])
    assert f["prediction_flips"] == int(((fp >= 0.5) != (q >= 0.5)).sum())
    assert f["accuracy_before"] == pytest.approx(((fp >= 0.5) == fy).mean(), abs=1e-4)
    assert calibrate(_oof(p, y))["frozen"] is None  # no saved frozen predictions


def test_a_model_that_ranks_worse_than_chance_is_not_calibrated():
    """A negative slope would turn the ranking upside down: refuse, never hide it."""
    p, y = _synthetic(2000, a_true=-0.5, b_true=0.0, seed=8)
    with pytest.raises(ValueError, match="reverse the model's ranking"):
        calibrate(_oof(p, y))


def test_a_calibration_file_is_written_once_and_read_back(tmp_path):
    path = tmp_path / "runs/calibration/cc200_abcd1234.json"
    assert read_calibration(path) is None
    write_calibration({"method": "platt", "a": 0.8, "b": -0.1}, path)
    back = read_calibration(path)
    assert back["a"] == 0.8 and "fitted_at" in back
    with pytest.raises(FileExistsError):
        write_calibration({"method": "platt", "a": 1.0, "b": 0.0}, path)
    path.write_text(json.dumps({"method": "isotonic"}))
    with pytest.raises(ValueError, match="unknown calibration method"):
        read_calibration(path)


# ---------------------------------------------------------------------------
# Inference applies the calibration file of the served run
# ---------------------------------------------------------------------------

def _registered_synthetic(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from neurographx.m3_model.model import GCN
    from neurographx.m3_model.run_logger import log_run, register_model
    from neurographx.m3_model.synthetic_brain import make_dataset

    torch.manual_seed(0)
    graphs = {g.subject_id: g for g in make_dataset(n_subjects=6, n_rois=20, seed=0)}
    model = GCN(20, 8, 2, num_layers=2, dropout=0.5)
    ckpt = tmp_path / "model.pt"
    torch.save({"state_dict": model.state_dict(), "in_dim": 20, "num_classes": 2,
                "hidden": 8, "layers": 2, "dropout": 0.5}, ckpt)
    log, registry = tmp_path / "run_log.jsonl", tmp_path / "registry.json"
    run_id = log_run({"run_id": "cafe1234", "dataset": "synthetic_brain", "atlas": "syn20",
                      "seed": 0, "hyperparameters": {}, "metrics": {},
                      "checkpoint_path": str(ckpt)}, log)
    register_model(run_id, log, registry)
    return graphs.__getitem__, registry, run_id


def test_inference_applies_the_calibration_file_of_the_served_run(tmp_path):
    from neurographx.m3_model.inference import predict

    get_graph, registry, run_id = _registered_synthetic(tmp_path)
    raw = predict("SYN_0000", "syn20", get_graph, registry)
    assert raw["calibrated"] is False

    cal = tmp_path / "calibration" / f"syn20_{run_id}.json"
    write_calibration({"method": "platt", "a": 1.0, "b": 0.0}, cal)  # the identity map
    same = predict("SYN_0000", "syn20", get_graph, registry)
    assert same["calibrated"] is True
    assert (same["prediction"], same["confidence"]) == (raw["prediction"], raw["confidence"])

    cal.unlink()
    write_calibration({"method": "platt", "a": 0.0, "b": 3.0}, cal)  # q = sigmoid(3)
    shifted = predict("SYN_0000", "syn20", get_graph, registry)
    assert shifted["prediction"] == "autism"
    assert shifted["confidence"] == pytest.approx(round(float(_sigmoid(3.0)), 4))


# ---------------------------------------------------------------------------
# End to end: train (fixture data), then the real calibration script
# ---------------------------------------------------------------------------

SMALL = ("--epochs", "3", "--hidden", "8", "--layers", "2", "--batch-size", "4")


def _run(tmp_path, env, script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                          cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)


def test_calibrate_script_on_a_fixture_final_run(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    (tmp_path / "data/splits").mkdir(parents=True)
    (tmp_path / "data/frozen").mkdir(parents=True)
    shutil.copy(FX / "data/splits/cv5_folds.csv", tmp_path / "data/splits/cv5_folds.csv")
    shutil.copy(FX / "data/frozen/frozen_eval_6.csv",
                tmp_path / "data/frozen/frozen_eval_100.csv")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    env.pop("NGX_DATA", None)
    connectomes = ("--connectomes", str(FX / "data/processed/connectomes"))

    done = _run(tmp_path, env, "train_gnn.py", *connectomes, "--stage", "cv", *SMALL)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    runs = [json.loads(x) for x in (tmp_path / "runs/run_log.jsonl").read_text().splitlines()]
    cv = runs[-1]
    done = _run(tmp_path, env, "train_gnn.py", *connectomes, "--stage", "final",
                "--epochs-from-cv", cv["run_id"])
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    final = json.loads((tmp_path / "runs/run_log.jsonl").read_text().splitlines()[-1])
    log_before = (tmp_path / "runs/run_log.jsonl").read_bytes()

    not_final = _run(tmp_path, env, "calibrate.py", "--run", cv["run_id"])
    assert not_final.returncode != 0 and "not a final run" in (not_final.stdout + not_final.stderr)
    done = _run(tmp_path, env, "calibrate.py", "--run", final["run_id"])
    atlas, rid = final["atlas"], final["run_id"]
    cal_file = tmp_path / f"runs/calibration/{atlas}_{rid}.json"
    # calibration is not a run: the run log is untouched either way
    assert (tmp_path / "runs/run_log.jsonl").read_bytes() == log_before
    if done.returncode != 0:
        # 12 fixture participants can give a CV model no better than chance: the script must
        # then refuse loudly and write nothing (the success path is tested on files below)
        assert "reverse the model's ranking" in done.stdout + done.stderr
        assert not cal_file.exists()
        return
    record = json.loads(cal_file.read_text())
    assert record["run_id"] == rid and record["cv_run_id"] == cv["run_id"]
    oof_file = tmp_path / record["oof_file"]
    assert record["oof_sha256"] == hashlib.sha256(oof_file.read_bytes()).hexdigest()
    assert record["frozen"]["n"] == 6
    assert (tmp_path / f"docs/reports/figures/calibration_{atlas}_{rid}.png").exists()

    again = _run(tmp_path, env, "calibrate.py", "--run", rid)
    assert again.returncode != 0 and "written once" in (again.stdout + again.stderr)


# ---------------------------------------------------------------------------
# The script's success path on files only: a logged CV run with a real OOF signal
# ---------------------------------------------------------------------------

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_calibrate_run_writes_the_file_and_figure_from_logged_runs(tmp_path, monkeypatch):
    import importlib.util

    from neurographx.m3_model.run_logger import log_run

    monkeypatch.chdir(tmp_path)
    rng = np.random.default_rng(9)
    dev_ids, frozen_ids = np.arange(1000, 1400), np.arange(5000, 5060)
    pd.DataFrame({"SUB_ID": dev_ids, "fold": np.arange(400) % 5}).to_csv("folds.csv", index=False)
    pd.DataFrame({"SUB_ID": frozen_ids}).to_csv("frozen.csv", index=False)

    def table(ids, folds):
        z = rng.normal(0, 3, len(ids))  # over-confident scores with a real signal
        y = (rng.random(len(ids)) < _sigmoid(0.3 * z)).astype(int)
        p = _sigmoid(z)
        df = pd.DataFrame({"SUB_ID": ids, "FILE_ID": [f"S_{i:07d}" for i in ids],
                           "SITE_ID": "SITE", "label": y, "prob_autism": p,
                           "prediction": (p >= 0.5).astype(int)})
        if folds is not None:
            df.insert(3, "fold", folds)
        return df

    Path("runs/oof").mkdir(parents=True)
    Path("runs/frozen_predictions").mkdir(parents=True)
    oof_path, fp_path = Path("runs/oof/cc200_cv000001_oof.csv"), \
        Path("runs/frozen_predictions/cc200_fin00001_frozen.csv")
    table(dev_ids, np.arange(400) % 5).to_csv(oof_path, index=False)
    table(frozen_ids, None).to_csv(fp_path, index=False)
    log = Path("runs/run_log.jsonl")
    log_run({"run_id": "cv000001", "stage": "cv", "dataset": "abide", "atlas": "cc200", "seed": 0,
             "hyperparameters": {}, "data_config": {}, "checkpoint_path": "none (cross-validation)",
             "metrics": {"oof": {"file": oof_path.as_posix(), "sha256": _sha(oof_path)}}}, log)
    log_run({"run_id": "fin00001", "stage": "final", "dataset": "abide", "atlas": "cc200",
             "seed": 0, "hyperparameters": {}, "checkpoint_path": "checkpoints/cc200_fin00001.pt",
             "data_config": {"folds_file": "folds.csv",
                             "folds_sha256": _sha(Path("folds.csv")),
                             "frozen_file": "frozen.csv",
                             "frozen_sha256": _sha(Path("frozen.csv"))},
             "metrics": {"cv_run_id": "cv000001",
                         "frozen": {"predictions": {"file": fp_path.as_posix(),
                                                    "sha256": _sha(fp_path)}}}}, log)

    spec = importlib.util.spec_from_file_location("calibrate_script", ROOT / "scripts/calibrate.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    record = script.calibrate_run("fin00001", log_path=log)

    assert 0 < record["a"] < 1  # over-confident model: the calibrator softens it
    assert record["oof"]["after_cross_fitted"]["ece"] < record["oof"]["before"]["ece"]
    assert record["frozen"]["n"] == 60
    written = json.loads(Path("runs/calibration/cc200_fin00001.json").read_text())
    assert written["oof_sha256"] == _sha(oof_path) and written["cv_run_id"] == "cv000001"
    assert Path("docs/reports/figures/calibration_cc200_fin00001.png").exists()

    # the same content with Windows line endings still matches its logged hash ...
    Path("runs/calibration/cc200_fin00001.json").unlink()
    oof_path.write_bytes(oof_path.read_bytes().replace(b"\n", b"\r\n"))
    assert script.calibrate_run("fin00001", log_path=log)["a"] == record["a"]

    # ... but changed content does not: refuse
    oof_path.write_bytes(oof_path.read_bytes() + b"1,2,3\r\n")
    Path("runs/calibration/cc200_fin00001.json").unlink()
    with pytest.raises(SystemExit, match="does not match the SHA-256"):
        script.calibrate_run("fin00001", log_path=log)
