"""Regenerate and export (memo 0013, part 3; work plan Section 5.1, Week 6).

Runs on a private copy of the fixture dataset (memo 0014). Regenerate really loads the
fixture checkpoint and predicts, so these tests need PyTorch and PyTorch Geometric
(both are in CI).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx.analysis_log import FIELDS  # noqa: E402
from neurographx.api.reproduce import compare  # noqa: E402
from neurographx.m3_model.run_logger import read_registry  # noqa: E402


def _analyse(api, participant_id="0090001", atlas="cc200"):
    response = api.post("/analyses", json={"participant_id": participant_id, "atlas": atlas})
    assert response.status_code == 201, response.json()
    return response.json()


def _log(root):
    path = root / "runs/analysis_log.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def _registered(root):
    return read_registry(root / "runs/model_registry.json")["cc200"]


def _new_model(root, scale=0.5):
    """Register a second CC200 model with changed weights, as a new final run would.

    The old run stays in the run log and moves to previous_run_ids, as register_model
    does (memo 0009, section 1). Returns the new run_id.
    """
    import torch

    old = _registered(root)
    ckpt = torch.load(root / old["checkpoint_path"], map_location="cpu")
    ckpt["state_dict"] = {k: v * scale if v.is_floating_point() else v
                          for k, v in ckpt["state_dict"].items()}
    new_id = "abcdef12"
    relative = f"checkpoints/cc200_{new_id}.pt"
    torch.save(ckpt, root / relative)

    runs = [json.loads(x) for x in (root / "runs/run_log.jsonl").read_text().splitlines()]
    run = dict(next(r for r in runs if r["run_id"] == old["run_id"]))
    run.update(run_id=new_id, checkpoint_path=relative,
               checkpoint_sha256=hashlib.sha256((root / relative).read_bytes()).hexdigest())
    with (root / "runs/run_log.jsonl").open("a") as fh:
        fh.write(json.dumps(run) + "\n")

    registry = read_registry(root / "runs/model_registry.json")
    registry["cc200"] = dict(old, run_id=new_id, checkpoint_path=relative,
                             previous_run_ids=[old["run_id"], *old["previous_run_ids"]])
    (root / "runs/model_registry.json").write_text(json.dumps(registry, indent=2))
    return new_id


# ---------------------------------------------------------------------------
# Regenerate: success
# ---------------------------------------------------------------------------

def test_regenerate_repeats_the_analysis_and_records_the_repeat(api, fixture_root):
    original = _analyse(api)
    response = api.post(f"/analyses/{original['analysis_id']}/regenerate")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"analysis", "original", "identical", "differences"}
    assert body["identical"] is True and body["differences"] == []
    assert body["original"] == original

    repeat = body["analysis"]
    assert set(repeat) == set(FIELDS)
    assert repeat["analysis_id"] != original["analysis_id"]
    assert repeat["reproduces_analysis_id"] == original["analysis_id"]
    for field in ("participant_id", "atlas", "run_id", "prediction", "confidence",
                  "calibrated"):
        assert repeat[field] == original[field]

    assert _log(fixture_root) == [original, repeat]  # appended; the original is unchanged
    assert api.get(f"/analyses/{repeat['analysis_id']}").json() == repeat


def test_regenerate_uses_the_original_run_not_the_registered_one(api, fixture_root):
    original = _analyse(api)
    new_id = _new_model(fixture_root)
    newer = _analyse(api)
    assert newer["run_id"] == new_id                       # new analyses use the new model
    assert newer["confidence"] != original["confidence"]   # which answers differently

    body = api.post(f"/analyses/{original['analysis_id']}/regenerate").json()
    assert body["analysis"]["run_id"] == original["run_id"]  # the old model, still served
    assert body["identical"] is True


def test_a_regenerated_analysis_can_itself_be_regenerated(api, fixture_root):
    original = _analyse(api, "0090003")
    first = api.post(f"/analyses/{original['analysis_id']}/regenerate").json()["analysis"]
    second = api.post(f"/analyses/{first['analysis_id']}/regenerate").json()
    assert second["identical"] is True
    assert second["analysis"]["reproduces_analysis_id"] == first["analysis_id"]
    assert len(_log(fixture_root)) == 3


def test_a_changed_calibration_is_reported_not_hidden(api, fixture_root):
    """Regenerate reports what differs; it never quietly returns the stored answer."""
    run_id = _registered(fixture_root)["run_id"]
    cal = fixture_root / f"runs/calibration/cc200_{run_id}.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"method": "platt", "a": 0.0, "b": 3.0}))  # q = sigmoid(3)
    original = _analyse(api)
    assert original["calibrated"] is True

    cal.unlink()  # the run's calibration file is gone
    body = api.post(f"/analyses/{original['analysis_id']}/regenerate").json()
    assert body["identical"] is False
    assert "calibrated" in body["differences"]
    assert body["analysis"]["calibrated"] is False


def test_compare_names_the_differing_fields_in_a_fixed_order():
    base = {"prediction": "autism", "confidence": 0.81, "calibrated": True}
    assert compare(base, dict(base)) == []
    assert compare(base, dict(base, confidence=0.8101)) == ["confidence"]
    assert compare(base, {"prediction": "control", "confidence": 0.6, "calibrated": False}) \
        == ["prediction", "confidence", "calibrated"]


# ---------------------------------------------------------------------------
# Regenerate: the documented errors
# ---------------------------------------------------------------------------

def test_regenerate_an_unknown_analysis_is_404(api):
    response = api.post("/analyses/0123456789ab/regenerate")
    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown analysis: 0123456789ab"


def test_regenerate_without_the_original_checkpoint_is_503(api, fixture_root):
    original = _analyse(api)
    (fixture_root / _registered(fixture_root)["checkpoint_path"]).unlink()
    response = api.post(f"/analyses/{original['analysis_id']}/regenerate")
    assert response.status_code == 503
    assert "is not available on this machine" in response.json()["detail"]
    assert len(_log(fixture_root)) == 1  # nothing recorded


def test_regenerate_with_a_changed_checkpoint_is_503(api, fixture_root):
    original = _analyse(api)
    ckpt = fixture_root / _registered(fixture_root)["checkpoint_path"]
    ckpt.write_bytes(ckpt.read_bytes() + b"\0")
    response = api.post(f"/analyses/{original['analysis_id']}/regenerate")
    assert response.status_code == 503 and "cannot be used" in response.json()["detail"]
    assert len(_log(fixture_root)) == 1


def test_regenerate_when_the_run_left_the_run_log_is_503(api, fixture_root):
    original = _analyse(api)
    path = fixture_root / "runs/run_log.jsonl"
    kept = [x for x in path.read_text().splitlines()
            if json.loads(x)["run_id"] != original["run_id"]]
    path.write_text("\n".join(kept) + "\n")
    response = api.post(f"/analyses/{original['analysis_id']}/regenerate")
    assert response.status_code == 503 and "not in the run log" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_json_is_the_stored_record_as_a_file(api):
    record = _analyse(api)
    response = api.get(f"/analyses/{record['analysis_id']}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == \
        f'attachment; filename="analysis_{record["analysis_id"]}.json"'
    assert response.json() == record
    assert list(response.json()) == list(FIELDS)  # the column order of db/schema.sql


def test_export_csv_is_a_header_and_one_row(api):
    record = _analyse(api)
    response = api.get(f"/analyses/{record['analysis_id']}/export", params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].endswith(
        f'filename="analysis_{record["analysis_id"]}.csv"')
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == list(FIELDS) and len(rows) == 2
    row = dict(zip(rows[0], rows[1], strict=True))
    assert row["analysis_id"] == record["analysis_id"]
    assert float(row["confidence"]) == record["confidence"]
    assert row["calibrated"] == ("true" if record["calibrated"] else "false")
    assert row["reproduces_analysis_id"] == ""  # null is an empty cell


def test_export_of_a_regenerated_analysis_carries_the_link(api):
    original = _analyse(api)
    repeat = api.post(f"/analyses/{original['analysis_id']}/regenerate").json()["analysis"]
    rows = list(csv.reader(io.StringIO(
        api.get(f"/analyses/{repeat['analysis_id']}/export?format=CSV").text)))
    assert dict(zip(rows[0], rows[1], strict=True))["reproduces_analysis_id"] == \
        original["analysis_id"]


def test_export_errors_follow_the_contract(api):
    record = _analyse(api)
    bad = api.get(f"/analyses/{record['analysis_id']}/export", params={"format": "xml"})
    assert bad.status_code == 422
    assert bad.json()["detail"] == "Unknown format 'xml'. Use one of: json, csv"
    missing = api.get("/analyses/0123456789ab/export")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Unknown analysis: 0123456789ab"
