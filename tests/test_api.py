"""Participant endpoints and the error contract (memo 0013; backlog W5-03, W5-04).

Quality status now comes from the committed QC outputs, not a live screen, so most tests
run on the fixture dataset (memo 0014) and a few build a tiny dataset with `make_dataset`.
No real participant data is used.
"""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("fastapi")  # skip locally until requirements are installed; CI has it

from neurographx.api import participants as pt  # noqa: E402
from neurographx.api.errors import validation_message  # noqa: E402


def cohort(root):
    return pd.read_csv(root / "data/splits/qc_cohort.csv")


def exclusions(root):
    return pd.read_csv(root / "docs/reports/exclusion_log.csv")


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(api):
    body = api.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["participant_table_found"] is True
    assert body["data_mode"] == "real"   # the mode comes from NGX_DATA, not from the root


def test_health_works_without_the_table(client_for, tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "data.yaml").write_text(
        (pt.datasource.data_root("fixtures") / "configs" / "data.yaml").read_text())
    response = client_for(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json()["participant_table_found"] is False


def test_default_path_comes_from_the_config():
    path = pt.table_path()
    assert path.name == "Phenotypic_V1_0b_preprocessed1.csv"
    assert path.parent.name == "raw"


# ---------------------------------------------------------------------------
# /participants: counts and the source of quality status
# ---------------------------------------------------------------------------

def test_counts_match_the_committed_qc_outputs(api, fixture_root):
    body = api.get("/participants").json()
    kept, log = cohort(fixture_root), exclusions(fixture_root)
    assert body["total"] == len(kept) + len(log) == len(body["participants"])
    assert body["included"] == len(kept)
    assert body["excluded"] == len(log)
    included = {int(p["participant_id"]) for p in body["participants"]
                if p["qc_status"] == "included"}
    assert included == set(kept.SUB_ID)


def test_completeness_exclusions_are_served(api):
    """The live screen could not see the completeness gate; the QC outputs can."""
    record = api.get("/participants/90012").json()
    assert record["qc_status"] == "excluded"
    assert record["exclusion_gate"] == "completeness"
    assert record["exclusion_reasons"] == ["missing rois_dosenbach160 file"]
    assert record["split"] is None


def test_split_tells_frozen_from_development(api, fixture_root):
    frozen = set(pd.read_csv(fixture_root / "data/frozen/frozen_eval_6.csv").SUB_ID)
    for p in api.get("/participants", params={"qc_status": "included"}).json()["participants"]:
        expected = "frozen" if int(p["participant_id"]) in frozen else "development"
        assert p["split"] == expected, p["participant_id"]


def test_every_reason_and_every_gate_from_the_log(api, fixture_root):
    by_id = {p["participant_id"]: p for p in api.get("/participants").json()["participants"]}
    for row in exclusions(fixture_root).itertuples(index=False):
        record = by_id[f"{row.SUB_ID:07d}"]
        assert record["exclusion_gate"] == row.first_gate_failed
        assert record["exclusion_reasons"] == [r.strip() for r in row.reasons.split(";")]


# ---------------------------------------------------------------------------
# /participants filters (W5-03)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("params", [
    {"site": "SYN_B"}, {"group": "autism"}, {"qc_status": "excluded"},
    {"site": "SYN_A", "group": "control"},
    {"site": "SYN_C", "group": "autism", "qc_status": "included"},
])
def test_filters_combine(api, params):
    everyone = api.get("/participants").json()["participants"]
    body = api.get("/participants", params=params).json()
    expected = [p for p in everyone if all(p[k] == v for k, v in params.items())]
    assert body["participants"] == expected
    assert body["total"] == len(everyone)            # counts are never filtered


def test_site_filter_ignores_case(api):
    lower = api.get("/participants", params={"site": "syn_b"}).json()["participants"]
    assert lower and all(p["site"] == "SYN_B" for p in lower)


@pytest.mark.parametrize("params, field", [
    ({"qc_status": "maybe"}, "qc_status"),
    ({"group": "asd"}, "group"),
])
def test_bad_filter_values_are_422_with_a_plain_sentence(api, params, field):
    response = api.get("/participants", params=params)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str)                    # never FastAPI's raw list
    assert field in detail and params[field] in detail


def test_unknown_site_is_422_and_lists_the_sites(api):
    response = api.get("/participants", params={"site": "NOWHERE"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "NOWHERE" in detail and "SYN_A" in detail


# ---------------------------------------------------------------------------
# /participants/{id}
# ---------------------------------------------------------------------------

def test_one_participant_by_either_id_form(api):
    padded, plain = api.get("/participants/0090001"), api.get("/participants/90001")
    assert padded.status_code == plain.status_code == 200
    assert padded.json() == plain.json()
    record = padded.json()
    assert record["participant_id"] == "0090001"
    assert record["group"] in ("autism", "control")
    assert record["sex"] in ("male", "female")
    assert set(record) == {"participant_id", "file_id", "site", "group", "sex", "age",
                           "qc_status", "exclusion_gate", "exclusion_reasons", "split"}


@pytest.mark.parametrize("unknown", ["9999999", "abc", "0090001x"])
def test_unknown_participant_is_404_with_detail(api, unknown):
    response = api.get(f"/participants/{unknown}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Unknown participant: {unknown}"


# ---------------------------------------------------------------------------
# Missing or inconsistent data: 503 with a plain sentence
# ---------------------------------------------------------------------------

def test_missing_table_is_503_not_a_crash(client_for, fixture_root):
    (fixture_root / "data/raw/Phenotypic_V1_0b_preprocessed1.csv").unlink()
    response = client_for(fixture_root).get("/participants")
    assert response.status_code == 503
    assert "01_fetch_phenotypic" in response.json()["detail"]


def test_missing_qc_outputs_are_503(client_for, fixture_root):
    (fixture_root / "docs/reports/exclusion_log.csv").unlink()
    response = client_for(fixture_root).get("/participants")
    assert response.status_code == 503
    assert "05_apply_qc" in response.json()["detail"]


def test_qc_outputs_out_of_step_with_the_table_are_503(client_for, fixture_root):
    path = fixture_root / "data/splits/qc_cohort.csv"
    kept = cohort(fixture_root)
    kept.iloc[1:].to_csv(path, index=False)          # one participant now in neither file
    response = client_for(fixture_root).get("/participants")
    assert response.status_code == 503
    assert "do not match" in response.json()["detail"]


def test_table_without_sub_id_is_a_clear_error(client_for, fixture_root):
    path = fixture_root / "data/raw/Phenotypic_V1_0b_preprocessed1.csv"
    pd.DataFrame({"SITE_ID": ["NYU"]}).to_csv(path, index=False)
    response = client_for(fixture_root).get("/participants")
    assert response.status_code == 503
    assert "SUB_ID" in response.json()["detail"]


# ---------------------------------------------------------------------------
# A hand-made dataset: reasons as the QC script words them
# ---------------------------------------------------------------------------

def test_reasons_name_the_failing_rule(client_for, make_dataset):
    table = pd.DataFrame({
        "SUB_ID": [50001, 50002, 50003, 50004, 50005],
        "FILE_ID": ["NYU_0050001", "NYU_0050002", "no_filename", "NYU_0050004", "NYU_0050005"],
        "SITE_ID": ["NYU"] * 5,
        "DX_GROUP": [1, 2, 1, 2, 1],
        "SEX": [1, 2, 1, 1, 2],
        "AGE_AT_SCAN": [10.5, 22.0, 15.25, None, 30.0],
        "qc_rater_1": ["OK", "fail", "OK", None, "OK"],
        "func_mean_fd": [0.1, 0.1, 0.1, 0.1, 0.62],
    })
    root = make_dataset(table, splits={"frozen": [50001]})
    body = client_for(root).get("/participants").json()
    by_id = {p["participant_id"]: p for p in body["participants"]}

    assert by_id["0050001"]["qc_status"] == "included"
    assert by_id["0050001"]["exclusion_reasons"] == []
    assert by_id["0050001"]["split"] == "frozen"
    assert by_id["0050001"]["file_id"] == "NYU_0050001"
    assert by_id["0050002"]["exclusion_reasons"] == ["qc_rater_1 = fail"]
    assert by_id["0050002"]["exclusion_gate"] == "rater"
    assert by_id["0050003"]["file_id"] is None and by_id["0050003"]["qc_status"] == "included"
    assert by_id["0050004"]["exclusion_reasons"] == ["qc_rater_1 = missing"]
    assert by_id["0050004"]["age"] is None
    assert by_id["0050005"]["exclusion_gate"] == "motion"
    assert by_id["0050005"]["exclusion_reasons"] == ["func_mean_fd = 0.620 > 0.5"]
    assert body["included"] == 2


def test_cache_notices_a_rerun_of_the_qc_script(client_for, make_dataset):
    table = pd.DataFrame({"SUB_ID": [50001, 50002], "SITE_ID": ["NYU", "NYU"],
                          "DX_GROUP": [1, 2]})
    root = make_dataset(table)
    client = client_for(root)
    assert client.get("/participants").json()["included"] == 2
    log = root / "docs/reports/exclusion_log.csv"
    kept = cohort(root)
    excluded_row = kept.iloc[[1]].assign(first_gate_failed="motion", gates_failed="motion",
                                         reasons="func_mean_fd missing")
    excluded_row.drop(columns=["mean_fd"]).to_csv(log, index=False)
    kept.iloc[[0]].to_csv(root / "data/splits/qc_cohort.csv", index=False)
    assert client.get("/participants").json()["included"] == 1


# ---------------------------------------------------------------------------
# The error contract itself
# ---------------------------------------------------------------------------

def test_validation_message_is_one_readable_sentence_per_error():
    message = validation_message([
        {"loc": ("query", "qc_status"), "msg": "Input should be 'included' or 'excluded'",
         "input": "maybe", "type": "literal_error"},
        {"loc": ("body", "atlas"), "msg": "Field required", "input": {}, "type": "missing"},
    ])
    assert message == ("Invalid value 'maybe' for qc_status: input should be 'included' or "
                       "'excluded'. Missing required field: atlas.")


def test_unexpected_errors_are_500_with_a_plain_detail(client_for, fixture_root, monkeypatch):
    def boom(_root=None):
        raise RuntimeError("something internal")
    monkeypatch.setattr(pt, "load_participants", boom)
    response = client_for(fixture_root, raise_server_exceptions=False).get("/participants")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error; see the server log."}
