"""Robustness (#140): every failure path returns its documented error (memo 0013, part 4).

One table of requests that must fail, each with its status and the words its sentence must
contain, run against a private copy of the fixture dataset (memo 0014). Every error body
must be {"detail": <one plain-language sentence>}: a string, on one line, starting with a
capital letter, so the dashboard can show it as it is. Nothing may be written to the
analysis log by a request that fails.

The paths that need a trained model (POST /analyses, regenerate) also need PyTorch;
the rest run without it.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")


def _assert_plain_sentence(response, status: int, words: str) -> None:
    assert response.status_code == status, (response.status_code, response.text)
    body = response.json()
    assert set(body) == {"detail"}, body
    detail = body["detail"]
    assert isinstance(detail, str) and detail, detail
    assert "\n" not in detail and detail[0].isupper(), detail
    assert words in detail, (words, detail)


def _log_lines(root) -> int:
    path = root / "runs/analysis_log.jsonl"
    return len(path.read_text().splitlines()) if path.exists() else 0


# (method, url, request body or None, status, words the sentence must contain)
DATA_SIDE = [
    ("get", "/participants/0099999", None, 404, "Unknown participant: 0099999"),
    ("get", "/participants?site=XYZ", None, 422, "Unknown site 'XYZ'"),
    ("get", "/participants?group=foo", None, 422, "for group"),
    ("get", "/participants?qc_status=maybe", None, 422, "for qc_status"),
    ("get", "/exclusions?gate=bad", None, 422, "for gate"),
    ("get", "/analyses?atlas=xyz", None, 422, "Unknown atlas 'xyz'"),
    ("get", "/analyses?participant_id=abc", None, 422, "Invalid participant_id 'abc'"),
    ("get", "/analyses?limit=0", None, 422, "for limit"),
    ("get", "/analyses?limit=5000", None, 422, "for limit"),
    ("get", "/analyses/doesnotexist", None, 404, "Unknown analysis: doesnotexist"),
    ("get", "/analyses/doesnotexist/export", None, 404, "Unknown analysis"),
    ("post", "/analyses/doesnotexist/regenerate", None, 404, "Unknown analysis"),
    ("get", "/models/xyz", None, 422, "Unknown atlas 'xyz'"),
    ("get", "/nope", None, 404, "No such endpoint: GET /nope."),
    ("put", "/analyses", None, 405, "Method PUT is not allowed for /analyses."),
]

# the five checks of POST /analyses, in their fixed order, and malformed bodies
ANALYSIS_REQUESTS = [
    ({"participant_id": "0090001", "atlas": "xyz"}, 422, "Unknown atlas 'xyz'"),
    ({"participant_id": "0099999", "atlas": "cc200"}, 404, "Unknown participant: 0099999"),
    ({"participant_id": "0090007", "atlas": "cc200"}, 409, "excluded by quality control"),
    ({"participant_id": "0090001", "atlas": "aal"}, 503, "Connectome data for atlas 'aal'"),
    ({"participant_id": "0090001", "atlas": "ho"}, 503, "No model is registered for atlas 'ho'"),
    ({"participant_id": "0090001"}, 422, "Missing required field: atlas."),
    ({}, 422, "Missing required field: participant_id."),
    ({"participant_id": 123, "atlas": ["cc200"]}, 422, "for participant_id"),
]


@pytest.mark.parametrize("method, url, body, status, words", DATA_SIDE,
                         ids=[f"{m.upper()} {u}" for m, u, *_ in DATA_SIDE])
def test_data_side_failures_are_documented_sentences(api, fixture_root, method, url, body,
                                                     status, words):
    response = getattr(api, method)(url) if body is None else getattr(api, method)(url,
                                                                                   json=body)
    _assert_plain_sentence(response, status, words)
    assert _log_lines(fixture_root) == 0


@pytest.mark.parametrize("body, status, words", ANALYSIS_REQUESTS,
                         ids=[json.dumps(b) for b, *_ in ANALYSIS_REQUESTS])
def test_every_failed_analysis_request_is_its_documented_error(api, fixture_root, body,
                                                               status, words):
    _assert_plain_sentence(api.post("/analyses", json=body), status, words)
    assert _log_lines(fixture_root) == 0


def test_a_body_that_is_not_json_is_one_sentence(api, fixture_root):
    response = api.post("/analyses", content="not json",
                        headers={"Content-Type": "application/json"})
    _assert_plain_sentence(response, 422, "The request body is not valid JSON.")
    assert _log_lines(fixture_root) == 0


def test_an_unexpected_error_is_500_with_one_sentence(client_for, fixture_root, monkeypatch):
    from neurographx.api import main

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated fault")

    monkeypatch.setattr(main, "run_analysis", boom)
    api = client_for(fixture_root, raise_server_exceptions=False)
    response = api.post("/analyses", json={"participant_id": "0090001", "atlas": "cc200"})
    _assert_plain_sentence(response, 500, "Internal error; see the server log.")
    assert "simulated fault" not in response.text  # internals are logged, not shown


# ---------------------------------------------------------------------------
# Paths that need the fixture model: export format, missing or changed checkpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def analysis_id(api):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    response = api.post("/analyses", json={"participant_id": "0090001", "atlas": "cc200"})
    assert response.status_code == 201
    return response.json()["analysis_id"]


def test_an_unknown_export_format_is_422(api, analysis_id):
    _assert_plain_sentence(api.get(f"/analyses/{analysis_id}/export?format=xml"), 422,
                           "Unknown format 'xml'. Use one of: json, csv")


def test_deleting_an_analysis_is_not_allowed(api, analysis_id, fixture_root):
    _assert_plain_sentence(api.delete(f"/analyses/{analysis_id}"), 405, "Method DELETE")
    assert _log_lines(fixture_root) == 1  # the record is still there


def _checkpoint(root):
    registry = json.loads((root / "runs/model_registry.json").read_text())
    return root / registry["cc200"]["checkpoint_path"]


@pytest.mark.parametrize("damage, words", [
    ("missing", "checkpoint"),
    ("changed", "cannot be used"),
])
def test_a_missing_or_changed_checkpoint_is_503_and_nothing_is_written(api, fixture_root,
                                                                      damage, words):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    ckpt = _checkpoint(fixture_root)
    if damage == "missing":
        ckpt.unlink()
    else:
        ckpt.write_bytes(ckpt.read_bytes() + b"\0")
    response = api.post("/analyses", json={"participant_id": "0090001", "atlas": "cc200"})
    _assert_plain_sentence(response, 503, words)
    assert _log_lines(fixture_root) == 0
