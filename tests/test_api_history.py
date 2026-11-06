"""GET /analyses and GET /analyses/{analysis_id} (memo 0013; backlog W5-07).

Analyses are written with the real writer into a private copy of the fixture dataset,
then read back through the API, as the dashboard's History page will.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from neurographx import analysis_log as al  # noqa: E402
from neurographx.m3_model.run_logger import read_registry  # noqa: E402


@pytest.fixture
def history(fixture_root):
    """Five analyses at known times, written through the analysis log writer."""
    run_id = read_registry(fixture_root / "runs/model_registry.json")["cc200"]["run_id"]
    log, runs = fixture_root / "runs/analysis_log.jsonl", fixture_root / "runs/run_log.jsonl"
    written = []
    for i, (pid, atlas) in enumerate([("0090001", "cc200"), ("0090003", "cc200"),
                                      ("0090001", "cc200"), ("0090005", "cc200"),
                                      ("0090001", "cc200")]):
        out = {"participant_id": pid, "atlas": atlas, "prediction": "control",
               "confidence": 0.7, "calibrated": False, "run_id": run_id}
        record = al.make_record(out, timestamp=f"2026-10-27T10:0{i}:00+00:00")
        written.append(al.write_analysis(record, log, runs))
    return written


def test_empty_history_is_an_empty_list_not_an_error(api):
    assert api.get("/analyses").json() == {"total": 0, "analyses": []}


def test_history_is_newest_first(api, history):
    body = api.get("/analyses").json()
    assert body["total"] == 5
    assert [a["analysis_id"] for a in body["analyses"]] == \
        [r["analysis_id"] for r in reversed(history)]


def test_history_filters_by_participant_in_either_id_form(api, history):
    for pid in ("0090001", "90001"):
        body = api.get("/analyses", params={"participant_id": pid}).json()
        assert body["total"] == 3
        assert all(a["participant_id"] == "0090001" for a in body["analyses"])


def test_history_filters_by_atlas(api, history):
    assert api.get("/analyses", params={"atlas": "cc200"}).json()["total"] == 5
    assert api.get("/analyses", params={"atlas": "ho"}).json()["total"] == 0


def test_limit_keeps_the_newest_and_total_counts_all(api, history):
    body = api.get("/analyses", params={"limit": 2}).json()
    assert body["total"] == 5
    assert [a["analysis_id"] for a in body["analyses"]] == \
        [history[4]["analysis_id"], history[3]["analysis_id"]]


@pytest.mark.parametrize("params, words", [
    ({"atlas": "cc400"}, ["Unknown atlas 'cc400'", "cc200"]),
    ({"participant_id": "abc"}, ["participant_id", "abc"]),
    ({"limit": 0}, ["limit"]),
    ({"limit": "many"}, ["limit"]),
])
def test_bad_history_parameters_are_422(api, params, words):
    response = api.get("/analyses", params=params)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str) and all(w in detail for w in words)


def test_one_record_by_id(api, history):
    record = history[1]
    response = api.get(f"/analyses/{record['analysis_id']}")
    assert response.status_code == 200
    assert response.json() == record


@pytest.mark.parametrize("unknown", ["ffffffffffff", "not-an-id"])
def test_unknown_analysis_is_404(api, history, unknown):
    response = api.get(f"/analyses/{unknown}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Unknown analysis: {unknown}"


def test_history_record_shape_is_the_contract(api, history):
    record = api.get("/analyses").json()["analyses"][0]
    assert list(record) == list(al.FIELDS)


def test_a_real_fixture_prediction_flows_into_history(api, fixture_root, monkeypatch):
    """The whole data path POST /analyses will use, minus the endpoint itself:
    check_request -> inference.predict on the fixture model -> log_prediction -> history."""
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from neurographx.api.analysis_checks import check_request
    from neurographx.m2_connectome.engine import load_atlas
    from neurographx.m3_model.data import make_get_graph
    from neurographx.m3_model.inference import predict

    ok = check_request("90001", "cc200", fixture_root)
    monkeypatch.chdir(fixture_root)  # load_model opens the checkpoint path from here (memo 0014)
    npz = fixture_root / "data/processed/connectomes/cpac_filt_global/rois_cc200.npz"
    get_graph = make_get_graph(load_atlas(npz), density=0.10)
    out = predict(ok["participant"]["participant_id"], "cc200", get_graph,
                  fixture_root / "runs/model_registry.json")
    record = al.log_prediction(out, fixture_root / "runs/analysis_log.jsonl",
                               fixture_root / "runs/run_log.jsonl")

    served = api.get(f"/analyses/{record['analysis_id']}").json()
    assert served == record
    assert served["run_id"] == ok["model"]["run_id"]
    assert served["prediction"] in ("autism", "control") and served["calibrated"] is False
    assert api.get("/analyses", params={"participant_id": "90001"}).json()["total"] == 1
