"""The API skeleton (issue #21): health and participant endpoints.

Uses the synthetic phenotypic table from conftest.py, never real participant data.
"""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("fastapi")  # skip locally until requirements are installed; CI has it

from fastapi.testclient import TestClient  # noqa: E402

from neurographx.api import participants as pt  # noqa: E402
from neurographx.api.main import app, get_criteria, get_motion, get_table_path  # noqa: E402
from neurographx.m1_ingestion import metadata as md  # noqa: E402
from neurographx.m1_ingestion import screening  # noqa: E402


@pytest.fixture
def client_for():
    def make(path, criteria=None, motion="config"):
        app.dependency_overrides[get_table_path] = lambda: path
        rules = criteria if criteria is not None else screening.rater_criteria()
        app.dependency_overrides[get_criteria] = lambda: rules
        gate = screening.motion_rule() if motion == "config" else motion
        app.dependency_overrides[get_motion] = lambda: gate
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


@pytest.fixture
def client(client_for, synthetic_phenotypic):
    return client_for(synthetic_phenotypic)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["participant_table_found"] is True


def test_health_works_without_the_table(client_for, tmp_path):
    response = client_for(tmp_path / "missing.csv").get("/health")
    assert response.status_code == 200
    assert response.json()["participant_table_found"] is False


def test_missing_table_is_503_not_a_crash(client_for, tmp_path):
    response = client_for(tmp_path / "missing.csv").get("/participants")
    assert response.status_code == 503
    assert "01_fetch_phenotypic" in response.json()["detail"]


def test_lists_every_row_with_consistent_counts(client, synthetic_phenotypic):
    body = client.get("/participants").json()
    rows = len(pd.read_csv(synthetic_phenotypic))
    assert body["total"] == rows == len(body["participants"])
    assert body["included"] + body["excluded"] == rows


def test_included_count_matches_the_m1_rater_filter(client_for, synthetic_phenotypic):
    """Given the same rules, the API and M1's metadata report agree on who passes."""
    client = client_for(synthetic_phenotypic, criteria=md.QC_ACCEPTED, motion=None)
    body = client.get("/participants").json()
    m1 = md.would_pass_all_raters(md.load_phenotypic(synthetic_phenotypic))
    assert body["included"] == m1["passing_all"]


def test_status_filter(client):
    body = client.get("/participants", params={"qc_status": "excluded"}).json()
    assert len(body["participants"]) == body["excluded"]
    assert all(p["qc_status"] == "excluded" for p in body["participants"])
    assert all(p["exclusion_reasons"] for p in body["participants"])


def test_bad_status_is_rejected(client):
    assert client.get("/participants", params={"qc_status": "maybe"}).status_code == 422


def test_one_participant_by_either_id_form(client):
    padded = client.get("/participants/0050001")
    plain = client.get("/participants/50001")
    assert padded.status_code == plain.status_code == 200
    assert padded.json() == plain.json()
    record = padded.json()
    assert record["participant_id"] == "0050001"
    assert record["group"] in ("autism", "control")
    assert record["sex"] in ("male", "female")


@pytest.mark.parametrize("unknown", ["9999999", "abc", "0050001x"])
def test_unknown_participant_is_404(client, unknown):
    assert client.get(f"/participants/{unknown}").status_code == 404


def test_reasons_name_the_failing_rule(client_for, tmp_path):
    table = pd.DataFrame(
        {
            "SUB_ID": [50001, 50002, 50003, 50004],
            "FILE_ID": ["NYU_0050001", "NYU_0050002", "no_filename", "NYU_0050004"],
            "SITE_ID": ["NYU"] * 4,
            "DX_GROUP": [1, 2, 1, 2],
            "SEX": [1, 2, 1, 1],
            "AGE_AT_SCAN": [10.5, 22.0, 15.25, None],
            "qc_rater_1": ["OK", "fail", "OK", None],
        }
    )
    path = tmp_path / "pheno.csv"
    table.to_csv(path, index=False)
    body = client_for(path).get("/participants").json()
    by_id = {p["participant_id"]: p for p in body["participants"]}

    assert by_id["0050001"]["qc_status"] == "included"
    assert by_id["0050001"]["exclusion_reasons"] == []
    assert by_id["0050001"]["file_id"] == "NYU_0050001"
    assert by_id["0050002"]["exclusion_reasons"] == ["qc_rater_1 is fail (accepted: OK)"]
    assert by_id["0050003"]["file_id"] is None
    assert "no_filename" in by_id["0050003"]["exclusion_reasons"][0]
    assert by_id["0050004"]["exclusion_reasons"] == ["qc_rater_1 is missing (accepted: OK)"]
    assert by_id["0050004"]["age"] is None
    assert body["included"] == 1


def test_table_without_sub_id_is_a_clear_error(client_for, tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"SITE_ID": ["NYU"]}).to_csv(path, index=False)
    response = client_for(path).get("/participants")
    assert response.status_code == 500
    assert "SUB_ID" in response.json()["detail"]


def test_default_path_comes_from_the_config():
    path = pt.table_path()
    assert path.name == "Phenotypic_V1_0b_preprocessed1.csv"
    assert path.parent.name == "raw"


def test_api_screen_matches_the_week2_qc_cohort_logic(client, synthetic_phenotypic):
    """One source of truth: with the closed memo 0003 rules (raters plus head motion),
    the API includes exactly the participants m1_ingestion.qc.apply_qc retains."""
    from neurographx.config import load
    from neurographx.m1_ingestion.qc import apply_qc

    df = md.load_phenotypic(synthetic_phenotypic)
    df["FILE_ID"] = [f"S_{i}" for i in df.SUB_ID]
    kept, _ = apply_qc(df, load("qc_criteria.yaml"), None, [])
    body = client.get("/participants", params={"qc_status": "included"}).json()
    assert {int(p["participant_id"]) for p in body["participants"]} == set(kept.SUB_ID)


def test_motion_reason_is_named(client_for, tmp_path):
    table = pd.DataFrame({"SUB_ID": [50001, 50002, 50003], "qc_rater_1": ["OK"] * 3,
                          "func_mean_fd": [0.1, 0.62, None]})
    path = tmp_path / "pheno.csv"
    table.to_csv(path, index=False)
    by_id = {p["participant_id"]: p for p in
             client_for(path).get("/participants").json()["participants"]}
    assert by_id["0050001"]["qc_status"] == "included"
    assert by_id["0050002"]["exclusion_reasons"] == [
        "func_mean_fd is 0.620 (accepted: at most 0.5 mm)"]
    assert by_id["0050003"]["exclusion_reasons"] == [
        "func_mean_fd is missing (head motion gate)"]
