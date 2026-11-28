"""GET /models, GET /models/ensemble and GET /models/{atlas} (memo 0013, W5-10; memo 0017)."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from neurographx import datasource  # noqa: E402
from neurographx.api import models as api_models  # noqa: E402
from neurographx.api.main import app  # noqa: E402
from neurographx.m3_model import ensemble as ens  # noqa: E402
from neurographx.m3_model.run_logger import read_registry  # noqa: E402
from tests.test_ensemble import _load_script  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    def make(mode):
        if mode == "real":
            monkeypatch.delenv("NGX_DATA", raising=False)
        else:
            monkeypatch.setenv("NGX_DATA", mode)
        app.dependency_overrides.clear()
        return TestClient(app)
    return make


def test_fixture_registry_lists_its_one_model(client):
    body = client("fixtures").get("/models").json()
    assert [m["atlas"] for m in body] == ["cc200"]
    model = body[0]
    # The fixture's run ID changes whenever the fixture is rebuilt (memo 0014), so the
    # test reads it from the fixture registry instead of pinning one value.
    registered = read_registry(datasource.model_registry())["cc200"]
    assert model["run_id"] == registered["run_id"]
    assert model["checkpoint_path"] == registered["checkpoint_path"]
    assert model["checkpoint_available"] is True        # committed fixture checkpoint
    assert model["graph"] == {"atlas_key": "rois_cc200", "density": 0.1, "fill_nan": 0.0}
    assert model["hyperparameters"]["layers"] >= 1
    assert model["calibrated"] is False and model["calibration"] is None
    assert "frozen" in model["metrics"]


def test_one_atlas_matches_the_list(client):
    c = client("fixtures")
    assert c.get("/models/cc200").json() == c.get("/models").json()[0]


def test_known_atlas_without_a_model_is_503(client):
    response = client("fixtures").get("/models/ho")
    assert response.status_code == 503
    assert response.json() == {"detail": "No model is registered for atlas 'ho'"}


def test_unknown_atlas_is_422_with_one_sentence(client):
    response = client("fixtures").get("/models/cc400")
    assert response.status_code == 422
    assert response.json()["detail"] == \
        "Unknown atlas 'cc400'. Use one of: aal, cc200, ho, dosenbach160"


def test_real_registry_serves_the_four_final_models(client):
    """Week 6: one measured, calibrated final model per atlas (memos 0010 and 0011)."""
    models = {m["atlas"]: m for m in client("real").get("/models").json()}
    assert set(models) == {"aal", "cc200", "ho", "dosenbach160"}
    # the CC200 baseline is replaced, not erased: it stays in the registry's history
    assert "00252f2b" in models["cc200"]["previous_run_ids"]
    for m in models.values():
        assert m["metrics"]["frozen"]["n"] == 100
        assert m["metrics"]["frozen"]["majority_baseline"] == 0.54
        assert m["calibrated"] is True
        assert isinstance(m["checkpoint_available"], bool)  # memo 0009


def test_calibration_file_is_reported_when_it_exists(client, monkeypatch, tmp_path):
    cal = {"method": "platt", "a": 1.1, "b": -0.2, "cv_run_id": "7d994761"}
    path = tmp_path / "cc200_calibration.json"
    path.write_text(json.dumps(cal), encoding="utf-8")
    monkeypatch.setattr(api_models, "calibration_file", lambda atlas, run_id: path)
    body = client("fixtures").get("/models/cc200").json()
    assert body["calibrated"] is True and body["calibration"] == cal


# ---------------------------------------------------------------------------
# GET /models/ensemble (memo 0017, section 5)
# ---------------------------------------------------------------------------

def test_ensemble_is_404_in_fixture_mode(client):
    response = client("fixtures").get("/models/ensemble")
    assert response.status_code == 404
    assert response.json() == {"detail": "The ensemble has not been measured on this dataset."}


def test_ensemble_is_404_when_only_another_dataset_was_measured(four_members, monkeypatch,
                                                                client):
    root, _ = four_members
    other = {"dataset": "ABIDE", "ensemble_id": "x", "timestamp": "t", "members": {},
             "rule": {}, "metrics": {"cv": {}, "frozen": {}}}
    (root / "runs/ensemble_log.jsonl").write_text(json.dumps(other) + "\n")
    monkeypatch.setattr(datasource, "data_root", lambda which=None: root)
    assert client("fixtures").get("/models/ensemble").status_code == 404


def test_ensemble_serves_the_recorded_measurement(four_members, monkeypatch, client):
    root, members = four_members
    assert _load_script().main(["--measure-once"], root=root, members=members) == 0
    record = ens.read_ensemble_log(root / "runs/ensemble_log.jsonl")[0]
    monkeypatch.setattr(datasource, "data_root", lambda which=None: root)

    c = client("fixtures")
    response = c.get("/models/ensemble")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"ensemble_id", "timestamp", "members", "rule", "metrics"}
    assert body["ensemble_id"] == record["ensemble_id"]
    assert body["timestamp"] == record["timestamp"]
    assert body["members"] == record["members"] == members
    assert body["rule"]["threshold"] == 0.5 and body["rule"]["memo"] == "0017"
    assert body["metrics"]["cv"] == record["metrics"]["cv"]
    assert body["metrics"]["frozen"] == record["metrics"]["frozen"]

    # GET /models stays one entry per atlas; "ensemble" is not read as an atlas name
    assert all(m["atlas"] != "ensemble" for m in c.get("/models").json())
    assert c.get("/models/cc400").status_code == 422
