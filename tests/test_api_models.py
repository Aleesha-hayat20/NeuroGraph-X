"""GET /models and GET /models/{atlas} (memo 0013, W5-10), on fixture and real registries."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from neurographx import datasource  # noqa: E402
from neurographx.api import models as api_models  # noqa: E402
from neurographx.api.main import app  # noqa: E402
from neurographx.m3_model.run_logger import read_registry  # noqa: E402


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


def test_real_registry_reports_the_cc200_baseline(client):
    body = client("real").get("/models/cc200").json()
    assert body["run_id"] == "00252f2b"
    assert body["metrics"]["frozen"]["accuracy"] == 0.63
    assert body["metrics"]["frozen"]["majority_baseline"] == 0.54
    assert body["hyperparameters"]["hidden"] == 64
    assert isinstance(body["checkpoint_available"], bool)  # not in git (memo 0009)


def test_calibration_file_is_reported_when_it_exists(client, monkeypatch, tmp_path):
    cal = {"method": "platt", "a": 1.1, "b": -0.2, "cv_run_id": "7d994761"}
    path = tmp_path / "cc200_calibration.json"
    path.write_text(json.dumps(cal), encoding="utf-8")
    monkeypatch.setattr(api_models, "calibration_file", lambda atlas, run_id: path)
    body = client("fixtures").get("/models/cc200").json()
    assert body["calibrated"] is True and body["calibration"] == cal
