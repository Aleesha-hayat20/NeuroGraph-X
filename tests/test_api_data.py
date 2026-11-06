"""GET /atlases, GET /cohort/summary, GET /exclusions (memo 0013; backlog W5-02), and the
fixed order of checks for POST /analyses (memo 0013 part 4; backlog W5-04).

All on the fixture dataset (memo 0014), which plants one case for every path:
CC200 has data and a model, Harvard-Oxford data but no model, AAL and Dosenbach 160 no data.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException  # noqa: E402

from neurographx.api.analysis_checks import check_request  # noqa: E402

REAL_REGION_COUNTS = {"aal": 116, "cc200": 200, "ho": 111, "dosenbach160": 161}


# ---------------------------------------------------------------------------
# /atlases
# ---------------------------------------------------------------------------

def test_atlases_lists_the_four_in_config_order(api):
    body = api.get("/atlases").json()
    assert [a["atlas"] for a in body] == ["aal", "cc200", "ho", "dosenbach160"]
    assert [a["key"] for a in body] == ["rois_aal", "rois_cc200", "rois_ho",
                                        "rois_dosenbach160"]
    assert all(a["label"] and a["family"] for a in body)


def test_atlas_states_match_the_fixture(api, fixture_root):
    by_name = {a["atlas"]: a for a in api.get("/atlases").json()}
    registry = json.loads((fixture_root / "runs/model_registry.json").read_text())

    assert by_name["cc200"]["data_available"] and by_name["cc200"]["model_registered"]
    assert by_name["cc200"]["run_id"] == registry["cc200"]["run_id"]
    assert by_name["ho"]["data_available"] and not by_name["ho"]["model_registered"]
    assert by_name["ho"]["run_id"] is None
    for name in ("aal", "dosenbach160"):
        assert not by_name[name]["data_available"]
        assert by_name[name]["n_regions"] is None
    for name in ("cc200", "ho"):
        assert by_name[name]["n_regions"] == REAL_REGION_COUNTS[name]


def test_a_broken_manifest_counts_as_no_data(client_for, fixture_root):
    manifest = fixture_root / "data/processed/connectomes/cpac_filt_global/rois_ho.json"
    manifest.write_text("not json")
    by_name = {a["atlas"]: a for a in client_for(fixture_root).get("/atlases").json()}
    assert by_name["ho"]["data_available"] is False


# ---------------------------------------------------------------------------
# /cohort/summary
# ---------------------------------------------------------------------------

def test_summary_counts_agree_with_the_qc_outputs(api, fixture_root):
    body = api.get("/cohort/summary").json()
    kept = pd.read_csv(fixture_root / "data/splits/qc_cohort.csv")
    log = pd.read_csv(fixture_root / "docs/reports/exclusion_log.csv")
    assert (body["total"], body["included"], body["excluded"]) == \
        (len(kept) + len(log), len(kept), len(log))
    assert body["excluded_by_gate"] == {
        g: int((log.first_gate_failed == g).sum()) for g in ("rater", "motion", "completeness")}
    assert sum(body["excluded_by_gate"].values()) == body["excluded"]


def test_summary_breakdowns_add_up(api):
    body = api.get("/cohort/summary").json()
    groups = body["by_group"]
    assert set(groups) == {"autism", "control"}
    assert sum(g["included"] for g in groups.values()) == body["included"]
    assert sum(g["excluded"] for g in groups.values()) == body["excluded"]
    assert [s["site"] for s in body["by_site"]] == ["SYN_A", "SYN_B", "SYN_C"]
    assert sum(s["included"] + s["excluded"] for s in body["by_site"]) == body["total"]
    assert body["by_split"]["frozen"] == 6
    assert body["by_split"]["frozen"] + body["by_split"]["development"] == body["included"]


# ---------------------------------------------------------------------------
# /exclusions
# ---------------------------------------------------------------------------

def test_exclusions_mirror_the_exclusion_log(api, fixture_root):
    body = api.get("/exclusions").json()
    log = pd.read_csv(fixture_root / "docs/reports/exclusion_log.csv")
    assert body["total"] == len(log) == len(body["exclusions"])
    by_id = {e["participant_id"]: e for e in body["exclusions"]}
    two_gates = by_id["0090024"]
    assert two_gates["first_gate_failed"] == "rater"
    assert two_gates["gates_failed"] == ["rater", "motion"]
    assert two_gates["reasons"] == ["qc_rater_1 = maybe", "func_mean_fd = 0.710 > 0.5"]
    assert by_id["0090007"]["file_id"] is None


@pytest.mark.parametrize("gate", ["rater", "motion", "completeness"])
def test_exclusions_filter_by_first_gate(api, gate):
    summary = api.get("/cohort/summary").json()
    body = api.get("/exclusions", params={"gate": gate}).json()
    assert body["total"] == summary["excluded_by_gate"][gate] > 0
    assert all(e["first_gate_failed"] == gate for e in body["exclusions"])


def test_unknown_gate_is_422(api):
    response = api.get("/exclusions", params={"gate": "vibes"})
    assert response.status_code == 422
    assert "gate" in response.json()["detail"]


# ---------------------------------------------------------------------------
# The fixed order of checks for POST /analyses (used by the model side)
# ---------------------------------------------------------------------------

def _status(fn) -> tuple[int, str]:
    with pytest.raises(HTTPException) as err:
        fn()
    return err.value.status_code, err.value.detail


@pytest.mark.parametrize("participant, atlas, status, text", [
    ("0090001", "cc400", 422, "Unknown atlas 'cc400'"),       # 1 atlas name
    ("0099999", "cc200", 404, "Unknown participant: 0099999"),  # 2 participant exists
    ("0090007", "cc200", 409, "excluded by quality control (rater)"),  # 3 included
    ("0090001", "aal", 503, "Connectome data for atlas 'aal'"),  # 4 data present
    ("0090001", "ho", 503, "No model is registered for atlas 'ho'"),  # 5 model registered
])
def test_each_check_gives_its_documented_error(fixture_root, participant, atlas, status, text):
    code, detail = _status(lambda: check_request(participant, atlas, fixture_root))
    assert code == status
    assert text in detail


def test_checks_run_in_the_fixed_order(fixture_root):
    """When a request breaks two rules, the earlier check is the one reported."""
    # excluded participant AND unknown atlas: the atlas (check 1)
    assert _status(lambda: check_request("0090007", "cc400", fixture_root))[0] == 422
    # unknown participant on an atlas without data: the participant (check 2)
    assert _status(lambda: check_request("0099999", "aal", fixture_root))[0] == 404
    # excluded participant on an atlas without a model: the exclusion (check 3)
    assert _status(lambda: check_request("90012", "ho", fixture_root))[0] == 409


def test_409_carries_every_reason(fixture_root):
    _, detail = _status(lambda: check_request("90024", "cc200", fixture_root))
    assert detail == ("Participant 0090024 was excluded by quality control (rater): "
                      "qc_rater_1 = maybe; func_mean_fd = 0.710 > 0.5")


def test_missing_checkpoint_is_503(fixture_root):
    registry = json.loads((fixture_root / "runs/model_registry.json").read_text())
    (fixture_root / registry["cc200"]["checkpoint_path"]).unlink()
    code, detail = _status(lambda: check_request("0090001", "cc200", fixture_root))
    assert code == 503 and "checkpoint" in detail


def test_a_valid_request_returns_what_inference_needs(fixture_root):
    out = check_request("90001", "cc200", fixture_root)
    assert out["participant"]["participant_id"] == "0090001"
    assert out["atlas"]["n_regions"] == 200
    assert out["model"]["run_id"] == out["atlas"]["run_id"]
    assert out["checkpoint"].is_file() and out["checkpoint"].is_absolute()
