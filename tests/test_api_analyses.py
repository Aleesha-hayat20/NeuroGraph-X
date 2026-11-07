"""POST /analyses (memo 0013, parts 2 to 4; backlog W5-09, card #73).

Runs on a private copy of the fixture dataset (memo 0014), which plants one participant
for every error case. The success path really loads the fixture checkpoint and predicts,
so these tests need PyTorch and PyTorch Geometric (both are in CI).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx.m3_model.run_logger import read_registry  # noqa: E402

FIELDS = {"analysis_id", "timestamp", "participant_id", "atlas", "run_id", "prediction",
          "confidence", "calibrated", "git_commit", "reproduces_analysis_id"}


def _post(api, participant_id, atlas):
    return api.post("/analyses", json={"participant_id": participant_id, "atlas": atlas})


def _log(root):
    path = root / "runs/analysis_log.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------

def test_an_analysis_is_created_recorded_and_readable(api, fixture_root):
    response = _post(api, "90001", "cc200")  # short id form is accepted
    assert response.status_code == 201
    record = response.json()
    assert set(record) == FIELDS
    assert record["participant_id"] == "0090001"  # responses use the 7-digit form
    assert record["run_id"] == read_registry(fixture_root / "runs/model_registry.json")[
        "cc200"]["run_id"]
    assert record["prediction"] in ("autism", "control")
    assert 0.5 <= record["confidence"] <= 1
    assert record["calibrated"] is False and record["reproduces_analysis_id"] is None

    assert _log(fixture_root) == [record]  # written once, exactly as returned
    assert api.get(f"/analyses/{record['analysis_id']}").json() == record
    assert api.get("/analyses").json()["total"] == 1


def test_the_api_gives_the_same_answer_as_the_inference_path(api, fixture_root):
    """POST /analyses adds checks and a record, never a different prediction."""
    from neurographx import datasource
    from neurographx.m3_model.data import load_connectomes, make_get_graph
    from neurographx.m3_model.inference import predict
    from neurographx.m3_model.run_logger import get_run

    registry = fixture_root / "runs/model_registry.json"
    run = get_run(read_registry(registry)["cc200"]["run_id"], fixture_root / "runs/run_log.jsonl")
    cfg = run["data_config"]
    cset = load_connectomes(datasource.connectome_dir(fixture_root), cfg["atlas_key"])
    direct = predict("0090003", "cc200", make_get_graph(cset, cfg["density"], cfg["fill_nan"]),
                     registry)
    via_api = _post(api, "0090003", "cc200").json()
    assert (via_api["prediction"], via_api["confidence"]) == \
        (direct["prediction"], direct["confidence"])


def test_each_request_is_a_new_analysis(api, fixture_root):
    first, second = (_post(api, "0090001", "cc200").json() for _ in range(2))
    assert first["analysis_id"] != second["analysis_id"]
    assert (first["prediction"], first["confidence"]) == (second["prediction"],
                                                          second["confidence"])
    assert len(_log(fixture_root)) == 2


def test_a_calibrated_run_gives_a_calibrated_record(api, fixture_root):
    run_id = read_registry(fixture_root / "runs/model_registry.json")["cc200"]["run_id"]
    cal = fixture_root / f"runs/calibration/cc200_{run_id}.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"method": "platt", "a": 0.0, "b": 3.0}))  # q = sigmoid(3)
    record = _post(api, "0090001", "cc200").json()
    assert record["calibrated"] is True
    assert (record["prediction"], record["confidence"]) == ("autism", 0.9526)


# ---------------------------------------------------------------------------
# The error contract: same checks, same order, plain sentences (memo 0013, part 4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("participant, atlas, status, text", [
    ("0090001", "cc400", 422, "Unknown atlas 'cc400'"),
    ("0099999", "cc200", 404, "Unknown participant: 0099999"),
    ("0090007", "cc200", 409, "excluded by quality control (rater)"),
    ("0090001", "aal", 503, "Connectome data for atlas 'aal'"),
    ("0090001", "ho", 503, "No model is registered for atlas 'ho'"),
])
def test_each_failed_check_is_its_documented_error(api, fixture_root, participant, atlas,
                                                   status, text):
    response = _post(api, participant, atlas)
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str) and text in response.json()["detail"]
    assert _log(fixture_root) == []  # nothing is recorded for a refused request


def test_an_incomplete_body_is_422_with_one_sentence(api):
    response = api.post("/analyses", json={"participant_id": "0090001"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_a_missing_checkpoint_is_503(api, fixture_root):
    registry = read_registry(fixture_root / "runs/model_registry.json")
    (fixture_root / registry["cc200"]["checkpoint_path"]).unlink()
    response = _post(api, "0090001", "cc200")
    assert response.status_code == 503 and "checkpoint" in response.json()["detail"]
    assert _log(fixture_root) == []


def test_a_checkpoint_that_does_not_match_its_logged_hash_is_refused(api, fixture_root):
    """The served model must be the one that was measured (schema 3, checkpoint_sha256)."""
    registry = read_registry(fixture_root / "runs/model_registry.json")
    ckpt = fixture_root / registry["cc200"]["checkpoint_path"]
    ckpt.write_bytes(ckpt.read_bytes() + b"\0")
    response = _post(api, "0090001", "cc200")
    assert response.status_code == 503
    assert "cannot be used" in response.json()["detail"]
    assert _log(fixture_root) == []
