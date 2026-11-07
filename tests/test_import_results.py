"""scripts/import_results.py: a results zip is imported only if it checks out."""
import hashlib
import importlib.util
import json
import zipfile

import pytest

from neurographx.utils.paths import project_root

spec = importlib.util.spec_from_file_location(
    "import_results", project_root() / "scripts/import_results.py")
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)

OLD = {"run_id": "aaaa0001", "stage": "cv", "atlas": "cc200", "metrics": {}}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _make(tmp_path, *, tamper_checkpoint=False, change_old_line=False):
    repo = tmp_path / "repo"
    (repo / "runs").mkdir(parents=True)
    (repo / "runs/run_log.jsonl").write_text(json.dumps(OLD) + "\n")
    ckpt, preds = b"model-bytes", b"SUB_ID,label,prob_autism,prediction\n1,0,0.2,0\n"
    final = {"run_id": "bbbb0002", "stage": "final", "atlas": "cc200",
             "checkpoint_path": "checkpoints/cc200_bbbb0002.pt", "checkpoint_sha256": _sha(ckpt),
             "metrics": {"frozen": {"accuracy": 0.6, "balanced_accuracy": 0.6, "auc": 0.65,
                                    "predictions": {"file": "runs/frozen_predictions/"
                                                    "cc200_bbbb0002_frozen.csv",
                                                    "sha256": _sha(preds)}}}}
    old = dict(OLD, atlas="aal") if change_old_line else OLD
    z = tmp_path / "w6_results.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("run_log.jsonl", json.dumps(old) + "\n" + json.dumps(final) + "\n")
        zf.writestr("model_registry.json", json.dumps({"cc200": {"run_id": "bbbb0002"}}))
        zf.writestr("checkpoints/cc200_bbbb0002.pt", ckpt + (b"x" if tamper_checkpoint else b""))
        zf.writestr("runs/frozen_predictions/cc200_bbbb0002_frozen.csv",
                    preds.replace(b"\n", b"\r\n"))  # a Windows copy still matches
        zf.writestr("runs/calibration/cc200_bbbb0002.json", json.dumps({"run_id": "bbbb0002"}))
        zf.writestr("figures/calibration_cc200_bbbb0002.png", b"png")
    return repo, z


def test_a_good_zip_is_imported(tmp_path):
    repo, z = _make(tmp_path)
    added = imp.check_and_import(z, repo)
    assert [r["run_id"] for r in added] == ["bbbb0002"]
    assert len((repo / "runs/run_log.jsonl").read_text().splitlines()) == 2
    for path in ("checkpoints/cc200_bbbb0002.pt", "runs/model_registry.json",
                 "runs/frozen_predictions/cc200_bbbb0002_frozen.csv",
                 "runs/calibration/cc200_bbbb0002.json",
                 "docs/reports/figures/calibration_cc200_bbbb0002.png"):
        assert (repo / path).exists(), path


@pytest.mark.parametrize("kwargs, message", [
    ({"tamper_checkpoint": True}, "checkpoint missing or its SHA-256 differs"),
    ({"change_old_line": True}, "append-only"),
])
def test_a_bad_zip_is_refused_and_nothing_is_copied(tmp_path, kwargs, message):
    repo, z = _make(tmp_path, **kwargs)
    before = (repo / "runs/run_log.jsonl").read_bytes()
    with pytest.raises(SystemExit, match=message):
        imp.check_and_import(z, repo)
    assert (repo / "runs/run_log.jsonl").read_bytes() == before
    assert not (repo / "checkpoints").exists()
