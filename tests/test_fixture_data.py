"""The fixture dataset (memo 0014): synthetic, but in exactly the real formats.

Four kinds of check:

1. Provenance: every committed fixture file matches MANIFEST.json, and the generator
   rebuilds the same dataset from its seed.
2. Same format as the real data: the 106 real phenotypic columns, the real QC rules,
   the real splits code, the real connectome engine, the real run logger and schema.
3. Internally consistent: cohort, splits, connectomes, run log and registry agree
   (a small version of the Week 6 integrity check).
4. The API runs on it with one setting, NGX_DATA=fixtures.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import pytest

from neurographx import fixture_data as fd
from neurographx.config import load
from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion import splits as sp
from neurographx.m1_ingestion.qc import apply_qc
from neurographx.m2_connectome import engine
from neurographx.m3_model.data import short_atlas_name
from neurographx.m3_model.run_logger import get_run, read_registry, read_runs
from neurographx.utils.db import connect, import_registry, import_run_log
from neurographx.utils.paths import project_root

ROOT = project_root()
FX = ROOT / "fixtures"
CFG = load("data.yaml", FX)
REAL_CFG = load("data.yaml")
PIPE = (CFG["pipeline"]["name"], CFG["pipeline"]["strategy"])


def fx(relative: str):
    return FX / relative


@pytest.fixture(scope="module")
def cohort() -> pd.DataFrame:
    return pd.read_csv(fx(CFG["cohort"]["file"]))


@pytest.fixture(scope="module")
def exclusions() -> pd.DataFrame:
    return pd.read_csv(fx(CFG["cohort"]["exclusion_log"]))


@pytest.fixture(scope="module")
def frozen() -> pd.DataFrame:
    return pd.read_csv(fx(CFG["frozen_evaluation_set"]["file"]))


@pytest.fixture(scope="module")
def folds() -> pd.DataFrame:
    return pd.read_csv(fx(CFG["development_splits"]["file"]))


# ---------------------------------------------------------------------------
# 1. Provenance
# ---------------------------------------------------------------------------

def test_every_fixture_file_matches_the_manifest():
    assert fd.manifest_problems(FX) == [], "Regenerate with scripts/build_fixtures.py --force"


def test_the_fixture_says_it_is_synthetic():
    assert "SYNTHETIC" in fx("README.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in fx("configs/data.yaml").read_text(encoding="utf-8")
    assert "SYNTHETIC" in CFG["dataset"]["name"]


def _flatten(d: dict, prefix: tuple = ()) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flatten(v, prefix + (k,)))
        else:
            out[prefix + (k,)] = v
    return out


def test_fixture_config_differs_from_the_real_one_only_where_declared():
    real, fixture = _flatten(REAL_CFG), _flatten(CFG)
    assert real.keys() == fixture.keys()
    differing = {k for k in real if real[k] != fixture[k]}
    assert differing == fd.CONFIG_DIFFERENCES


def test_generator_rebuilds_the_same_dataset(tmp_path):
    fd.build(tmp_path, train_model=False, log=lambda *_: None)
    for name in ("data/raw/Phenotypic_V1_0b_preprocessed1.csv", "data/splits/qc_cohort.csv",
                 "docs/reports/exclusion_log.csv", CFG["frozen_evaluation_set"]["file"],
                 CFG["development_splits"]["file"], "configs/data.yaml"):
        assert sp.sha256_text(tmp_path / name) == sp.sha256_text(fx(name)), name
    for key in fd.CONNECTOME_ATLASES:
        new = engine.load_atlas(*engine.atlas_paths(tmp_path / CFG["connectome"]["output_dir"],
                                                    *PIPE, key))
        old = engine.load_atlas(*engine.atlas_paths(fx(CFG["connectome"]["output_dir"]),
                                                    *PIPE, key))
        # Same inputs, byte for byte (the fingerprint hashes every time series file) ...
        assert new.manifest["input_fingerprint"] == old.manifest["input_fingerprint"]
        # ... and the same matrices, up to float32 rounding on a different CPU.
        np.testing.assert_allclose(new.z_triu, old.z_triu, atol=1e-5, equal_nan=True)
        np.testing.assert_array_equal(new.zero_var, old.zero_var)


def test_generator_refuses_to_delete_a_folder_it_did_not_write(tmp_path):
    (tmp_path / "precious.txt").write_text("keep me")
    with pytest.raises(FileExistsError, match="MANIFEST"):
        fd.build(tmp_path, train_model=False, force=True, log=lambda *_: None)
    assert (tmp_path / "precious.txt").exists()


# ---------------------------------------------------------------------------
# 2. The real formats
# ---------------------------------------------------------------------------

def _documented_real_columns() -> list[str]:
    """Section 8 of the Week 1 metadata report: every column of the real file, in order."""
    text = (ROOT / "docs/reports/metadata_report.md").read_text(encoding="utf-8")
    block = text.split("## 8. All column names")[1].split("```")[1]
    return [re.sub(r"^\s*\d+\.\s", "", line) for line in block.strip("\n").splitlines()]


def test_phenotypic_columns_are_the_106_real_columns_in_order():
    header = list(pd.read_csv(fx("data/raw/Phenotypic_V1_0b_preprocessed1.csv"), nrows=0))
    assert header == fd.PHENOTYPIC_COLUMNS == _documented_real_columns()
    assert len(header) == 106


def test_fixture_ids_cannot_collide_with_real_abide_ids(cohort, exclusions):
    fixture_ids = set(cohort.SUB_ID) | set(exclusions.SUB_ID)
    assert min(fixture_ids) >= fd.FIRST_SUB_ID
    real_ids = set(pd.read_csv(ROOT / REAL_CFG["cohort"]["file"]).SUB_ID)
    assert max(real_ids) < fd.FIRST_SUB_ID
    assert not fixture_ids & real_ids


def test_qc_outputs_are_exactly_what_the_real_qc_code_writes(cohort, exclusions):
    """Re-run memo 0003's screen on the fixture table with the REAL rules."""
    df = md.load_phenotypic(fx("data/raw/Phenotypic_V1_0b_preprocessed1.csv"))
    kept, log = apply_qc(df, load("qc_criteria.yaml"), None, [])
    pd.testing.assert_frame_equal(kept, cohort, check_dtype=False)
    pd.testing.assert_frame_equal(log, exclusions, check_dtype=False)


def test_every_gate_and_every_rule_edge_appears(cohort, exclusions):
    by_id = exclusions.set_index("SUB_ID")
    assert set(by_id.index) == set(fd.EXCLUDED)
    assert by_id.loc[90007, "FILE_ID"] == "no_filename"
    assert by_id.loc[90016, "first_gate_failed"] == "motion"
    assert by_id.loc[90023, "reasons"] == "func_mean_fd missing"
    assert by_id.loc[90024, "gates_failed"] == "rater;motion"
    assert "qc_rater_1 = maybe" in by_id.loc[90024, "reasons"]
    kept = cohort.set_index("SUB_ID")
    assert kept.loc[90010, "mean_fd"] == 0.5          # at the limit: retained
    assert {90002, 90003} <= set(kept.index)           # "maybe" from rater 2: retained
    assert set(cohort.DX_GROUP) == {1, 2} and cohort.SITE_ID.nunique() == 3


def test_frozen_set_is_the_real_draw_and_its_hashes_hold(cohort, frozen):
    meta = json.loads(fx(CFG["frozen_evaluation_set"]["meta"]).read_text(encoding="utf-8"))
    fz = CFG["frozen_evaluation_set"]
    drawn, _ = sp.stratified_draw(cohort, fz["size"], fz["stratify_by"], fz["seed"])
    pd.testing.assert_frame_equal(drawn[sp.KEY_COLUMNS].reset_index(drop=True), frozen,
                                  check_dtype=False)
    assert meta["frozen_sha256"] == sp.sha256_text(fx(fz["file"]))
    assert meta["cohort_sha256"] == sp.sha256_text(fx(CFG["cohort"]["file"]))
    assert meta["size"] == len(frozen) == fd.FROZEN_SIZE


def test_folds_are_the_real_assignment_and_do_not_leak(cohort, frozen, folds):
    dv = CFG["development_splits"]
    pool = cohort[~cohort.SUB_ID.isin(frozen.SUB_ID)]
    expected = sp.make_folds(pool, dv["folds"], dv["stratify_by"], dv["seed"])
    pd.testing.assert_frame_equal(expected, folds, check_dtype=False)
    sp.assert_no_leakage(sp.training_rows(folds), frozen, context="fixture folds")
    assert set(folds.SUB_ID) | set(frozen.SUB_ID) == set(cohort.SUB_ID)


@pytest.mark.parametrize("key", fd.CONNECTOME_ATLASES)
def test_connectomes_load_through_the_engine_with_their_hash(key, cohort):
    cset = engine.load_atlas(*engine.atlas_paths(fx(CFG["connectome"]["output_dir"]), *PIPE,
                                                 key), verify_hash=True)
    assert cset.n_regions == fd.REGION_COUNTS[key]           # the real atlas sizes
    assert list(cset.file_ids) == list(cohort.FILE_ID)       # engine order = cohort order
    flat = {sub: cols for (atlas, sub), cols in fd.FLAT_REGIONS.items() if atlas == key}
    for i, sub in enumerate(cset.sub_ids):
        assert sorted(np.flatnonzero(cset.zero_var[i])) == sorted(flat.get(int(sub), []))
    m = cset.matrix(int(cset.sub_ids[0]), "z")
    assert np.allclose(m, m.T, equal_nan=True)


def test_connectome_files_have_exactly_the_format_the_engine_writes_today(tmp_path):
    """Build a 3-participant atlas with today's engine and compare the structure."""
    rng = np.random.default_rng(0)
    ts_dir = tmp_path / "ts"
    ts_dir.mkdir()
    toy = pd.DataFrame({"SUB_ID": [1, 2, 3], "FILE_ID": ["T_1", "T_2", "T_3"]})
    for fid in toy.FILE_ID:
        fd.write_1d(ts_dir / f"{fid}_rois_toy.1D", rng.standard_normal((30, 5)))
    engine.build_atlas("rois_toy", toy, ts_dir, tmp_path / "out", *PIPE)
    ref_npz, ref_json = engine.atlas_paths(tmp_path / "out", *PIPE, "rois_toy")
    fx_npz, fx_json = engine.atlas_paths(fx(CFG["connectome"]["output_dir"]), *PIPE,
                                         "rois_cc200")
    with np.load(ref_npz) as ref, np.load(fx_npz) as got:
        assert set(ref.files) == set(got.files)
        for name in ref.files:
            assert ref[name].dtype.kind == got[name].dtype.kind, name
            assert ref[name].ndim == got[name].ndim, name

    def keys(d, prefix=""):
        return {prefix + k for k in d} | {x for k, v in d.items() if isinstance(v, dict)
                                          for x in keys(v, prefix + k + ".")}
    ref_m = json.loads(ref_json.read_text())
    got_m = json.loads(fx_json.read_text())
    assert keys(ref_m) == keys(got_m)
    assert got_m["engine_version"] == engine.ENGINE_VERSION


def test_time_series_are_reproducible_from_the_seed(cohort, tmp_path):
    """Regenerating the inputs reproduces the input fingerprint stored in the manifest."""
    key = "rois_ho"
    _, manifest_path = engine.atlas_paths(fx(CFG["connectome"]["output_dir"]), *PIPE, key)
    manifest = json.loads(manifest_path.read_text())
    length = {site: n for site, _, n in fd.SITES}
    paths = []
    for row in cohort.itertuples(index=False):
        path = tmp_path / f"{row.FILE_ID}_{key}.1D"
        fd.write_1d(path, fd.make_timeseries(row.SUB_ID, row.DX_GROUP, length[row.SITE_ID],
                                             fd.REGION_COUNTS[key], key))
        paths.append(path)
    assert engine.input_fingerprint(manifest["parameters"], list(cohort.FILE_ID), paths) \
        == manifest["input_fingerprint"]


# ---------------------------------------------------------------------------
# 3. Run log, registry, checkpoint: consistent with each other and with the data
# ---------------------------------------------------------------------------

def test_registry_points_at_logged_runs_and_files_that_exist():
    registry = read_registry(fx("runs/model_registry.json"))
    assert set(registry) == {short_atlas_name(fd.MODEL_ATLAS)}   # cc200 only, ho has no model
    entry = registry["cc200"]
    run = get_run(entry["run_id"], fx("runs/run_log.jsonl"))
    assert run is not None and run["stage"] == "final"
    assert run["dataset"] == fd.DATASET_NAME
    assert run["repeat_frozen_measurement"] is False
    assert fx(entry["checkpoint_path"]).exists()
    assert entry["checkpoint_path"] == run["checkpoint_path"]
    cv = get_run(entry["metrics"]["cv_run_id"], fx("runs/run_log.jsonl"))
    assert cv is not None and cv["stage"] == "cv"


def test_runs_record_the_hashes_of_the_files_they_trained_on():
    """The Week 6 integrity check in miniature: recorded hashes match the files."""
    for run in read_runs(fx("runs/run_log.jsonl")):
        dc = run["data_config"]
        assert dc["folds_sha256"] == engine.sha256_file(fx(dc["folds_file"]))
        assert dc["frozen_sha256"] == engine.sha256_file(fx(dc["frozen_file"]))
        npz, _ = engine.atlas_paths(fx(CFG["connectome"]["output_dir"]), *PIPE,
                                    dc["atlas_key"])
        assert dc["connectome_sha256"] == engine.sha256_file(npz)


def test_fixture_logs_import_into_the_real_database_schema(tmp_path):
    conn = connect(tmp_path / "fixture.sqlite", ROOT / "db/schema.sql")
    assert import_run_log(conn, fx("runs/run_log.jsonl")) == 2
    assert import_registry(conn, fx("runs/model_registry.json")) == 1
    conn.close()


# ---------------------------------------------------------------------------
# 3b. The tiny model, through the real inference path (needs PyTorch)
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_model(monkeypatch):
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from neurographx.m3_model.data import make_get_graph

    # inference.load_model resolves the registry's relative checkpoint path against the
    # working directory, so run from the fixture root (memo 0014, open item for memo 0009).
    monkeypatch.chdir(FX)
    cset = engine.load_atlas(*engine.atlas_paths(fx(CFG["connectome"]["output_dir"]), *PIPE,
                                                 fd.MODEL_ATLAS))
    return cset, make_get_graph(cset, fd.DENSITY, fd.FILL_NAN)


def test_predict_returns_the_contract_on_fixture_data(fixture_model, frozen):
    from neurographx.m3_model.inference import predict

    _, get_graph = fixture_model
    pid = f"{int(frozen.SUB_ID.iloc[0]):07d}"                 # API-style id, "0090001"
    out = predict(pid, "cc200", get_graph, fx("runs/model_registry.json"))
    assert set(out) == {"participant_id", "atlas", "prediction", "confidence",
                        "calibrated", "run_id"}
    assert out["prediction"] in {"autism", "control"}
    assert 0.5 <= out["confidence"] <= 1.0
    assert out["run_id"] == read_registry(fx("runs/model_registry.json"))["cc200"]["run_id"]
    assert predict(pid, "cc200", get_graph, fx("runs/model_registry.json")) == out


def test_no_model_for_harvard_oxford_is_a_clear_error(fixture_model):
    from neurographx.m3_model.inference import predict

    _, get_graph = fixture_model
    with pytest.raises(KeyError, match="no model registered"):
        predict("0090001", "ho", get_graph, fx("runs/model_registry.json"))


def test_recorded_frozen_metrics_reproduce_from_the_checkpoint(fixture_model, frozen):
    """Reloading the committed checkpoint on this machine gives the recorded result."""
    from neurographx.m3_model.inference import load_model, predict_graph

    _, get_graph = fixture_model
    model, entry = load_model("cc200", fx("runs/model_registry.json"))
    preds = [predict_graph(model, get_graph(int(s)))[0] for s in frozen.SUB_ID]
    y = (frozen.DX_GROUP == 1).astype(int).to_numpy()
    tn = int(((np.array(preds) == 0) & (y == 0)).sum())
    fp = int(((np.array(preds) == 1) & (y == 0)).sum())
    fn = int(((np.array(preds) == 0) & (y == 1)).sum())
    tp = int(((np.array(preds) == 1) & (y == 1)).sum())
    assert [tn, fp, fn, tp] == entry["metrics"]["frozen"]["confusion_tn_fp_fn_tp"]


def test_tiny_model_predicts_both_classes_across_the_cohort(fixture_model, cohort):
    """So the dashboard shows both outcomes in fixture mode."""
    from neurographx.m3_model.inference import load_model, predict_graph

    _, get_graph = fixture_model
    model, _ = load_model("cc200", fx("runs/model_registry.json"))
    labels = {predict_graph(model, get_graph(int(s)))[0] for s in cohort.SUB_ID}
    assert labels == {0, 1}


# ---------------------------------------------------------------------------
# 4. The API on the fixture, with one setting
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_client(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from neurographx.api.main import app

    monkeypatch.setenv("NGX_DATA", "fixtures")
    app.dependency_overrides.clear()
    return TestClient(app)


def test_health_reports_fixture_mode(fixture_client):
    body = fixture_client.get("/health").json()
    assert body["data_mode"] == "fixtures"
    assert body["participant_table_found"] is True


def test_participant_counts_match_the_fixture_qc_outputs(fixture_client, cohort, exclusions):
    body = fixture_client.get("/participants").json()
    assert (body["total"], body["included"], body["excluded"]) == \
        (len(cohort) + len(exclusions), len(cohort), len(exclusions))
    included = {int(p["participant_id"]) for p in body["participants"]
                if p["qc_status"] == "included"}
    assert included == set(cohort.SUB_ID)


def test_exclusion_reasons_come_through_the_api(fixture_client):
    record = fixture_client.get("/participants/90007").json()
    assert record["qc_status"] == "excluded"
    assert record["file_id"] is None
    assert any("no_filename" in r for r in record["exclusion_reasons"])
    boundary = fixture_client.get("/participants/0090010").json()
    assert boundary["qc_status"] == "included" and boundary["exclusion_reasons"] == []


def test_real_participants_are_not_served_in_fixture_mode(fixture_client):
    assert fixture_client.get("/participants/0050003").status_code == 404
