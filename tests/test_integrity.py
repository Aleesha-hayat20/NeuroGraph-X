"""The integrity check (scripts/check_integrity.py, src/neurographx/integrity.py; Week 6).

Each test breaks one thing in a private copy of the fixture dataset (memo 0014) and checks
that the integrity check fails for that reason, and only fails when something is wrong.
The replay section needs PyTorch and PyTorch Geometric (both are in CI); the other tests
skip the replay so they stay fast.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import pytest

from neurographx.integrity import FAIL, PASS, WARN, check, text_hash_matches
from neurographx.utils.paths import project_root


def _failures(report):
    return [f.message for f in report.findings if f.status == FAIL]


def _check(root, replay=False):
    return check(root, "fixtures", replay=replay)


def _runs(root):
    path = root / "runs/run_log.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _write_runs(root, runs):
    (root / "runs/run_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))


def _registry(root):
    return json.loads((root / "runs/model_registry.json").read_text())


def _write_registry(root, registry):
    (root / "runs/model_registry.json").write_text(json.dumps(registry, indent=2))


def _final(root):
    entry = _registry(root)["cc200"]
    return next(r for r in _runs(root) if r["run_id"] == entry["run_id"])


# ---------------------------------------------------------------------------
# The committed fixture is consistent
# ---------------------------------------------------------------------------

def test_the_fixture_dataset_passes(fixture_root):
    report = _check(fixture_root)
    assert report.ok, _failures(report)
    assert report.count(PASS) >= 10


def test_the_fixture_dataset_passes_with_the_replay(fixture_root):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    report = _check(fixture_root, replay=True)
    assert report.ok, _failures(report)
    assert any("gives the saved probabilities" in f.message for f in report.findings
               if f.status == PASS)


def test_the_script_exits_0_on_the_fixture_and_prints_a_summary():
    root = project_root()
    out = subprocess.run([sys.executable, "scripts/check_integrity.py", "--data", "fixtures",
                          "--no-replay", "--quiet"], cwd=root, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "Integrity check passed:" in out.stdout and "0 failed" in out.stdout


def test_the_script_exits_1_when_something_fails(fixture_root):
    (fixture_root / _registry(fixture_root)["cc200"]["checkpoint_path"]).unlink()
    out = subprocess.run([sys.executable, "scripts/check_integrity.py", "--root",
                          str(fixture_root), "--data", "fixtures", "--no-replay"],
                         cwd=project_root(), capture_output=True, text=True)
    assert out.returncode == 1
    assert "Integrity check FAILED" in out.stdout


# ---------------------------------------------------------------------------
# 1 and 2: run log, registry, checkpoints
# ---------------------------------------------------------------------------

def test_a_duplicate_run_id_fails(fixture_root):
    runs = _runs(fixture_root)
    _write_runs(fixture_root, [*runs, runs[0]])  # what a careless union merge could leave
    assert any("used more than once" in m for m in _failures(_check(fixture_root)))


def test_a_registered_run_missing_from_the_run_log_fails(fixture_root):
    run_id = _registry(fixture_root)["cc200"]["run_id"]
    _write_runs(fixture_root, [r for r in _runs(fixture_root) if r["run_id"] != run_id])
    assert any("is not in the run log" in m for m in _failures(_check(fixture_root)))


def test_a_changed_checkpoint_fails(fixture_root):
    ckpt = fixture_root / _registry(fixture_root)["cc200"]["checkpoint_path"]
    ckpt.write_bytes(ckpt.read_bytes() + b"\0")
    assert any("does not match the SHA-256" in m for m in _failures(_check(fixture_root)))


def test_a_missing_checkpoint_fails(fixture_root):
    (fixture_root / _registry(fixture_root)["cc200"]["checkpoint_path"]).unlink()
    assert any("is missing" in m for m in _failures(_check(fixture_root)))


def test_registry_metrics_that_differ_from_the_run_fail(fixture_root):
    registry = _registry(fixture_root)
    registry["cc200"]["metrics"]["frozen"]["accuracy"] = 0.99
    _write_registry(fixture_root, registry)
    assert any("frozen-set metrics differ" in m for m in _failures(_check(fixture_root)))


def test_an_archived_run_without_its_checkpoint_is_only_a_warning(fixture_root):
    registry = _registry(fixture_root)
    old = dict(_final(fixture_root), run_id="0a0b0c0d",
               checkpoint_path="checkpoints/cc200_0a0b0c0d.pt")
    _write_runs(fixture_root, [*_runs(fixture_root), old])
    registry["cc200"]["previous_run_ids"] = ["0a0b0c0d"]
    _write_registry(fixture_root, registry)
    report = _check(fixture_root)
    assert report.ok, _failures(report)
    assert any("archived run 0a0b0c0d" in f.message for f in report.findings
               if f.status == WARN)


# ---------------------------------------------------------------------------
# 3 and 4: training files and the cohort
# ---------------------------------------------------------------------------

def test_split_files_with_windows_line_endings_still_match(fixture_root):
    folds = fixture_root / "data/splits/cv5_folds.csv"
    folds.write_bytes(folds.read_bytes().replace(b"\n", b"\r\n"))
    report = _check(fixture_root)
    assert report.ok, _failures(report)


def test_a_changed_split_file_fails(fixture_root):
    folds = fixture_root / "data/splits/cv5_folds.csv"
    lines = folds.read_text().splitlines()
    first, second = lines[1].rsplit(",", 1), lines[2].rsplit(",", 1)
    lines[1], lines[2] = f"{first[0]},{second[1]}", f"{second[0]},{first[1]}"  # swap folds
    folds.write_text("\n".join(lines) + "\n")
    assert any("differs from the file it trained with" in m
               for m in _failures(_check(fixture_root)))


def test_a_changed_out_of_fold_file_fails(fixture_root):
    cv_id = _final(fixture_root)["metrics"]["cv_run_id"]
    cv = next(r for r in _runs(fixture_root) if r["run_id"] == cv_id)
    oof = fixture_root / cv["metrics"]["oof"]["file"]
    oof.write_text(oof.read_text().replace("0.", "0.1", 1))
    assert any(f"cv run {cv_id}" in m and "does not match its hash" in m
               for m in _failures(_check(fixture_root)))


def _calibration(root, **change):
    final = _final(root)
    cv = next(r for r in _runs(root) if r["run_id"] == final["metrics"]["cv_run_id"])
    record = {"atlas": "cc200", "run_id": final["run_id"], "cv_run_id": cv["run_id"],
              "oof_sha256": cv["metrics"]["oof"]["sha256"], "method": "platt",
              "a": 1.0, "b": 0.0}
    record.update(change)
    path = root / f"runs/calibration/cc200_{final['run_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))


def test_a_calibration_file_fitted_on_its_runs_oof_file_passes(fixture_root):
    _calibration(fixture_root)
    report = _check(fixture_root)
    assert report.ok, _failures(report)
    assert not [f for f in report.findings if f.status == WARN and "calibration" in f.message]
    assert any("fitted on its cv run's out-of-fold file" in f.message
               for f in report.findings if f.status == PASS)


def test_a_calibration_file_fitted_on_another_oof_file_fails(fixture_root):
    _calibration(fixture_root, oof_sha256="0" * 64)
    assert any("out-of-fold file other than" in m for m in _failures(_check(fixture_root)))


def test_a_frozen_participant_in_the_folds_fails(fixture_root):
    frozen = (fixture_root / "data/frozen/frozen_eval_6.csv").read_text().splitlines()
    folds = fixture_root / "data/splits/cv5_folds.csv"
    folds.write_text(folds.read_text() + frozen[1] + ",0\n")
    assert any("in both the frozen set and the folds" in m
               for m in _failures(_check(fixture_root)))


def test_a_participant_in_neither_qc_file_fails(fixture_root):
    path = fixture_root / "docs/reports/exclusion_log.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n")  # drop the last excluded participant
    assert any("in neither file" in m for m in _failures(_check(fixture_root)))


def test_text_hash_matches_accepts_either_line_ending_and_nothing_else(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes(b"a,b\n1,2\n")
    lf = hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    crlf = hashlib.sha256(b"a,b\r\n1,2\r\n").hexdigest()
    assert text_hash_matches(path, lf) and text_hash_matches(path, crlf)
    assert not text_hash_matches(path, hashlib.sha256(b"a,b\n1,3\n").hexdigest())


# ---------------------------------------------------------------------------
# 5 and 6: connectome store and replay
# ---------------------------------------------------------------------------

def _store(root):
    return root / "data/processed/connectomes/cpac_filt_global"


def test_a_store_changed_after_it_was_built_fails(fixture_root):
    npz = _store(fixture_root) / "rois_cc200.npz"
    npz.write_bytes(npz.read_bytes() + b"\0")
    assert any("does not match its own manifest" in m for m in _failures(_check(fixture_root)))


def _as_another_build(root):
    """Make the run log say the model trained on a different file build of the store."""
    runs = _runs(root)
    for r in runs:
        if (r.get("data_config") or {}).get("connectome_sha256"):
            r["data_config"]["connectome_sha256"] = "f" * 64
    _write_runs(root, runs)


def test_another_build_without_a_replay_fails(fixture_root):
    _as_another_build(fixture_root)
    assert any("no replay confirmed" in m for m in _failures(_check(fixture_root)))


def test_another_build_is_accepted_when_the_replay_matches(fixture_root):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    _as_another_build(fixture_root)
    report = _check(fixture_root, replay=True)
    assert report.ok, _failures(report)
    assert any("built on another machine" in f.message for f in report.findings
               if f.status == PASS)


def test_a_replay_that_differs_fails(fixture_root):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    final = _final(fixture_root)
    meta = final["metrics"]["frozen"]["predictions"]
    path = fixture_root / meta["file"]
    lines = path.read_text().splitlines()
    head, rows = lines[0].split(","), [x.split(",") for x in lines[1:]]
    col = head.index("prob_autism")
    rows[0][col] = f"{min(1.0, float(rows[0][col]) + 0.05):.6f}" if float(rows[0][col]) < 0.9 \
        else f"{float(rows[0][col]) - 0.05:.6f}"
    path.write_text("\n".join([lines[0], *(",".join(r) for r in rows)]) + "\n")
    new_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    runs = _runs(fixture_root)  # keep the hashes consistent, so only the replay can notice
    for r in runs:
        if r["run_id"] == final["run_id"]:
            r["metrics"]["frozen"]["predictions"]["sha256"] = new_hash
    _write_runs(fixture_root, runs)
    registry = _registry(fixture_root)
    registry["cc200"]["metrics"]["frozen"]["predictions"]["sha256"] = new_hash
    _write_registry(fixture_root, registry)
    failures = _failures(_check(fixture_root, replay=True))
    assert any("differs from its saved probabilities" in m for m in failures)


# ---------------------------------------------------------------------------
# 7: analysis log
# ---------------------------------------------------------------------------

def _record(root, **change):
    record = {"analysis_id": "0123456789ab", "timestamp": "2026-11-08T10:00:00+00:00",
              "participant_id": "0090001", "atlas": "cc200",
              "run_id": _registry(root)["cc200"]["run_id"], "prediction": "autism",
              "confidence": 0.8, "calibrated": False, "git_commit": None,
              "reproduces_analysis_id": None}
    record.update(change)
    return record


def _write_analyses(root, records):
    (root / "runs/analysis_log.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records))


def test_analyses_written_through_the_api_pass(fixture_root, client_for):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    api = client_for(fixture_root)
    first = api.post("/analyses", json={"participant_id": "0090001", "atlas": "cc200"}).json()
    api.post(f"/analyses/{first['analysis_id']}/regenerate")
    report = _check(fixture_root)
    assert report.ok, _failures(report)
    assert any("2 analyses (1 regenerated)" in f.message for f in report.findings)


def test_an_analysis_by_an_unregistered_run_fails(fixture_root):
    cv_id = _final(fixture_root)["metrics"]["cv_run_id"]  # in the run log, but not served
    _write_analyses(fixture_root, [_record(fixture_root, run_id=cv_id)])
    assert any("neither registered nor archived" in m for m in _failures(_check(fixture_root)))


def test_a_duplicate_analysis_id_fails(fixture_root):
    _write_analyses(fixture_root, [_record(fixture_root), _record(fixture_root)])
    assert any("used more than once" in m for m in _failures(_check(fixture_root)))


def test_a_reproduction_of_another_participant_fails(fixture_root):
    original = _record(fixture_root)
    repeat = _record(fixture_root, analysis_id="ba9876543210", participant_id="0090003",
                     reproduces_analysis_id=original["analysis_id"])
    _write_analyses(fixture_root, [original, repeat])
    assert any("another participant" in m for m in _failures(_check(fixture_root)))


def test_a_reproduction_of_a_later_record_fails(fixture_root):
    original = _record(fixture_root)
    repeat = _record(fixture_root, analysis_id="ba9876543210",
                     reproduces_analysis_id=original["analysis_id"])
    _write_analyses(fixture_root, [repeat, original])
    assert any("not an earlier record" in m for m in _failures(_check(fixture_root)))


def test_an_invalid_record_fails(fixture_root):
    _write_analyses(fixture_root, [_record(fixture_root, confidence=1.7)])
    assert any("confidence" in m for m in _failures(_check(fixture_root)))


def test_the_committed_fixture_still_passes_after_the_tests():
    """Every test above works on a private copy, so the repository's fixture is untouched."""
    report = check(project_root() / "fixtures", "fixtures", replay=False)
    assert report.ok, _failures(report)
