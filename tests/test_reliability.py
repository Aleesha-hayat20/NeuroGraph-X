"""Reliability engine skeleton (memo 0016): manifest, splits and the resumable runner.

Everything runs on the synthetic fixture dataset (memo 0014), copied into a temporary
folder, with output in another temporary folder. Most runner tests use a stand-in
trainer, so they check the bookkeeping (manifest, resume, run log) in a few seconds;
two tests train the real GCN on one job each.
"""
import copy
import hashlib
import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from neurographx.m1_ingestion.splits import LeakageError
from neurographx.m5_reliability.manifest import (
    AXES,
    ManifestError,
    expand,
    jobs_of,
    load_spec,
    manifest_path,
    write_manifest,
)
from neurographx.m5_reliability.variants import SplitError, bootstrap, splits_for
from neurographx.utils.paths import project_root

ROOT = project_root()
SPEC = ROOT / "configs" / "reliability" / "fixture_grid.yaml"
POOL = pd.read_csv(ROOT / "fixtures" / "data" / "splits" / "cv5_folds.csv")
FROZEN = pd.read_csv(ROOT / "fixtures" / "data" / "frozen" / "frozen_eval_6.csv")
SITES = sorted(POOL["SITE_ID"].unique())


def _spec(**changes):
    spec = load_spec(SPEC)
    for key, value in changes.items():
        spec[key] = value
    return spec


def _write_spec(tmp_path, spec, name="grid.yaml"):
    import yaml
    path = tmp_path / name
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return path


def fake_trainer(train, evaluate, settings, seed):
    """Stands in for the GCN: a fixed, seed-dependent probability per participant."""
    return np.linspace(0.2, 0.8, len(evaluate)) * (1 + seed % 3) / 3


def _records(out):
    path = out / "runs" / "run_log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def test_fixture_grid_expands_to_sixteen_jobs_with_the_four_values():
    manifest = expand(load_spec(SPEC), SITES)
    jobs = jobs_of(manifest)
    assert len(jobs) == 16
    counts = {axis: sum(j.axis == axis for j in jobs) for axis in AXES}
    assert counts == {"atlas": 2, "seed": 4, "resample": 4, "site": 6}
    for job in manifest["jobs"]:
        assert {"axis", "value", "atlas", "seed", "job_id"} == set(job)
    assert {j.value for j in jobs if j.axis == "site"} == set(SITES)
    assert {j.atlas for j in jobs} == {"rois_cc200", "rois_ho"}


def test_the_same_definition_gives_the_same_identifiers():
    a, b = expand(load_spec(SPEC), SITES), expand(load_spec(SPEC), SITES)
    assert a["manifest_id"] == b["manifest_id"]
    assert [j["job_id"] for j in a["jobs"]] == [j["job_id"] for j in b["jobs"]]


def test_any_change_to_the_definition_changes_every_identifier():
    base = expand(load_spec(SPEC), SITES)
    spec = load_spec(SPEC)
    spec["settings"]["epochs"] = 11
    changed = expand(spec, SITES)
    assert changed["manifest_id"] != base["manifest_id"]
    assert not {j["job_id"] for j in changed["jobs"]} & {j["job_id"] for j in base["jobs"]}


@pytest.mark.parametrize("change, message", [
    ({"axes": {"weather": [1]}}, "unknown axis"),
    ({"atlases": []}, "no atlas"),
    ({"axes": {"seed": 3}}, "list of seeds"),
    ({"axes": {"resample": 0}}, "number of resamples"),
    ({"axes": {"site": ["SYN_Z"]}}, "not in the development pool"),
    ({"axes": {"seed": [1, 1]}}, "repeats a job"),
])
def test_invalid_definitions_are_refused(change, message):
    with pytest.raises(ManifestError, match=message):
        expand(_spec(**change), SITES)


def test_missing_settings_are_refused():
    spec = load_spec(SPEC)
    del spec["settings"]["epochs"]
    with pytest.raises(ManifestError, match="epochs"):
        expand(spec, SITES)


def test_a_manifest_is_written_once_and_never_replaced(tmp_path):
    manifest = expand(load_spec(SPEC), SITES)
    path = write_manifest(manifest, tmp_path)
    assert path == manifest_path(tmp_path, "fixture-v1")
    first = path.read_bytes()
    write_manifest(manifest, tmp_path)                 # same definition: no change
    assert path.read_bytes() == first
    spec = load_spec(SPEC)
    spec["settings"]["lr"] = 0.01
    with pytest.raises(ManifestError, match="new name"):
        write_manifest(expand(spec, SITES), tmp_path)
    assert path.read_bytes() == first


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------

def _job(axis, value, seed=42):
    return next(j for j in jobs_of(expand(load_spec(SPEC), SITES))
                if j.axis == axis and j.value == value and j.atlas == "rois_cc200"
                and j.seed == seed)


@pytest.mark.parametrize("axis, value, seed", [("atlas", "rois_cc200", 42), ("seed", 1, 1)])
def test_atlas_and_seed_jobs_use_the_five_folds_unchanged(axis, value, seed):
    splits = splits_for(_job(axis, value, seed), POOL)
    assert len(splits) == 5
    evaluated = pd.concat([s.evaluate for s in splits])
    assert sorted(evaluated["SUB_ID"]) == sorted(POOL["SUB_ID"])   # each once
    for s in splits:
        assert not set(s.train["SUB_ID"]) & set(s.evaluate["SUB_ID"])


def test_a_resample_is_a_stratified_bootstrap_scored_out_of_bag():
    train, oob = bootstrap(POOL, 42, 0)
    assert len(train) == len(POOL)
    assert train["DX_GROUP"].value_counts().to_dict() == POOL["DX_GROUP"].value_counts().to_dict()
    assert train["SUB_ID"].isin(POOL["SUB_ID"]).all()
    assert len(oob) > 0 and not set(oob["SUB_ID"]) & set(train["SUB_ID"])
    again, _ = bootstrap(POOL, 42, 0)
    other, _ = bootstrap(POOL, 42, 1)
    assert again["SUB_ID"].tolist() == train["SUB_ID"].tolist()
    assert other["SUB_ID"].tolist() != train["SUB_ID"].tolist()
    split, = splits_for(_job("resample", 0), POOL)
    assert split.evaluate["SUB_ID"].tolist() == oob["SUB_ID"].tolist()


def test_a_site_job_evaluates_only_the_site_it_leaves_out():
    for site in SITES:
        split, = splits_for(_job("site", site), POOL)
        assert set(split.evaluate["SITE_ID"]) == {site}
        assert site not in set(split.train["SITE_ID"])
        assert len(split.train) + len(split.evaluate) == len(POOL)


def test_a_site_split_needs_both_diagnoses_in_training():
    pool = POOL.copy()
    pool.loc[pool["SITE_ID"] != "SYN_A", "DX_GROUP"] = 1
    with pytest.raises(SplitError, match="one diagnosis"):
        splits_for(_job("site", "SYN_A"), pool)


def test_a_pool_without_the_needed_columns_is_refused():
    with pytest.raises(SplitError, match="SITE_ID"):
        splits_for(_job("seed", 1, 1), POOL.drop(columns="SITE_ID"))


# ---------------------------------------------------------------------------
# Runner (needs PyTorch Geometric to build graphs)
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    pytest.importorskip("torch")
    pytest.importorskip("torch_geometric")
    from neurographx.m5_reliability import runner as module
    return module


def _run(runner, fixture_root, out, spec=SPEC, **kwargs):
    kwargs.setdefault("trainer", fake_trainer)
    return runner.run_grid(spec, out, "fixtures", data_root=fixture_root,
                           echo=lambda _line: None, **kwargs)


def test_the_full_grid_logs_one_variant_run_per_job(runner, fixture_root, tmp_path):
    out = tmp_path / "out"
    summary = _run(runner, fixture_root, out)
    records = _records(out)
    assert len(records) == summary.total == 16 and summary.remaining == 0
    manifest = json.loads(summary.manifest_file.read_text())
    assert {r["reliability"]["job_id"] for r in records} == {j["job_id"] for j in manifest["jobs"]}
    frozen_ids = set(FROZEN["SUB_ID"])
    for r in records:
        assert r["stage"] == "variant" and r["dataset"] == "synthetic_fixture"
        assert r["checkpoint_path"] == "none (reliability variant)"
        assert r["reliability"]["manifest_id"] == manifest["manifest_id"]
        assert r["reliability"]["grid"] == "fixture-v1"
        pred = r["metrics"]["predictions"]
        path = out / pred["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pred["sha256"]
        table = pd.read_csv(path)
        assert len(table) == pred["n"] == r["metrics"]["pooled"]["n"]
        assert not set(table["SUB_ID"]) & frozen_ids           # frozen set never scored
        assert r["data_config"]["frozen_sha256"] and r["data_config"]["folds_sha256"]


def test_a_stopped_grid_resumes_where_it_stopped(runner, fixture_root, tmp_path):
    out = tmp_path / "out"
    first = _run(runner, fixture_root, out, max_jobs=5)
    assert len(first.ran) == 5 and first.remaining == 11
    second = _run(runner, fixture_root, out)
    assert second.done_before == 5 and len(second.ran) == 11 and second.remaining == 0
    third = _run(runner, fixture_root, out)
    assert third.done_before == 16 and third.ran == []
    job_ids = [r["reliability"]["job_id"] for r in _records(out)]
    assert len(job_ids) == len(set(job_ids)) == 16


def test_a_job_that_fails_is_not_logged_and_runs_again(runner, fixture_root, tmp_path):
    out = tmp_path / "out"
    calls = {"n": 0}

    def breaks_in_second_job(train, evaluate, settings, seed):
        calls["n"] += 1
        if calls["n"] == 7:            # job 1 is folds 1 to 5; call 7 is inside job 2
            raise RuntimeError("stopped")
        return fake_trainer(train, evaluate, settings, seed)

    with pytest.raises(RuntimeError, match="stopped"):
        _run(runner, fixture_root, out, trainer=breaks_in_second_job)
    assert len(_records(out)) == 1                     # only the finished job
    summary = _run(runner, fixture_root, out)
    assert summary.done_before == 1 and summary.remaining == 0
    assert len(_records(out)) == 16


def test_a_dry_run_writes_nothing(runner, fixture_root, tmp_path):
    out = tmp_path / "out"
    summary = _run(runner, fixture_root, out, dry_run=True)
    assert summary.remaining == 16 and summary.ran == []
    assert not out.exists()


def test_real_data_is_refused_without_the_flag(runner, tmp_path):
    with pytest.raises(runner.RealDataRefused, match="FYP-II"):
        runner.run_grid(SPEC, tmp_path / "out", "real", echo=lambda _l: None)
    assert not (tmp_path / "out").exists()


def test_fixture_mode_refuses_a_pool_that_is_not_synthetic(runner, fixture_root, tmp_path):
    folds = fixture_root / "data" / "splits" / "cv5_folds.csv"
    table = pd.read_csv(folds)
    table["SITE_ID"] = table["SITE_ID"].str.replace("SYN_", "NYU_")
    table.to_csv(folds, index=False)
    with pytest.raises(runner.RealDataRefused):
        _run(runner, fixture_root, tmp_path / "out")


def test_output_inside_the_fixture_dataset_is_refused(runner, fixture_root):
    with pytest.raises(runner.OutputRefused):
        _run(runner, fixture_root, ROOT / "fixtures" / "scratch")
    assert not (ROOT / "fixtures" / "scratch").exists()


def test_a_frozen_participant_in_the_pool_stops_the_run_before_training(runner, fixture_root,
                                                                        tmp_path):
    folds = fixture_root / "data" / "splits" / "cv5_folds.csv"
    table = pd.read_csv(folds)
    leaked = FROZEN.iloc[[0]][["SUB_ID", "FILE_ID", "SITE_ID", "DX_GROUP"]].assign(fold=0)
    pd.concat([table, leaked], ignore_index=True).to_csv(folds, index=False)

    def must_not_train(*_args):
        raise AssertionError("trained despite a leak")

    with pytest.raises(LeakageError):
        _run(runner, fixture_root, tmp_path / "out", trainer=must_not_train)
    assert _records(tmp_path / "out") == []


def test_a_changed_grid_under_the_same_name_logs_nothing(runner, fixture_root, tmp_path):
    out = tmp_path / "out"
    _run(runner, fixture_root, out, max_jobs=1)
    spec = copy.deepcopy(load_spec(SPEC))
    spec["settings"]["epochs"] = 3
    with pytest.raises(ManifestError):
        _run(runner, fixture_root, out, spec=_write_spec(tmp_path, spec))
    assert len(_records(out)) == 1


def test_a_trainer_must_return_one_probability_per_participant(runner, fixture_root, tmp_path):
    with pytest.raises(ValueError, match="probabilities"):
        _run(runner, fixture_root, tmp_path / "out", trainer=lambda *a: np.array([0.5]))


def test_variant_runs_import_into_the_database(runner, fixture_root, tmp_path):
    from neurographx.utils.db import connect, import_run_log
    out = tmp_path / "out"
    _run(runner, fixture_root, out, max_jobs=3)
    conn = connect(tmp_path / "db.sqlite", ROOT / "db" / "schema.sql")
    assert import_run_log(conn, out / "runs" / "run_log.jsonl") == 3
    rows = conn.execute("SELECT stage, reliability FROM run_log").fetchall()
    assert {stage for stage, _ in rows} == {"variant"}
    assert all(json.loads(rel)["axis"] for _, rel in rows)
    conn.close()


def test_the_real_gcn_gives_the_same_predictions_twice(runner, fixture_root, tmp_path):
    """One real job, trained twice from scratch: same seed, same probabilities."""
    a = _run(runner, fixture_root, tmp_path / "a", max_jobs=1, trainer=runner.gcn_trainer)
    b = _run(runner, fixture_root, tmp_path / "b", max_jobs=1, trainer=runner.gcn_trainer)
    ra, rb = _records(tmp_path / "a")[0], _records(tmp_path / "b")[0]
    assert a.ran and b.ran and ra["run_id"] != rb["run_id"]
    assert ra["metrics"]["predictions"]["sha256"] == rb["metrics"]["predictions"]["sha256"]
    probs = pd.read_csv(tmp_path / "a" / ra["metrics"]["predictions"]["file"])["prob_autism"]
    assert probs.between(0, 1).all()


def test_the_command_line_runs_and_refuses(tmp_path):
    pytest.importorskip("torch_geometric")
    script = str(ROOT / "scripts" / "run_reliability.py")
    dry = subprocess.run([sys.executable, script, "--spec", str(SPEC), "--output",
                          str(tmp_path / "out"), "--dry-run"],
                         capture_output=True, text=True, cwd=ROOT)
    assert dry.returncode == 0, dry.stderr
    assert "16 jobs, 0 already logged, 16 to run" in dry.stdout
    real = subprocess.run([sys.executable, script, "--spec", str(SPEC), "--output",
                           str(tmp_path / "out"), "--data", "real"],
                          capture_output=True, text=True, cwd=ROOT)
    assert real.returncode == 2 and "Refused" in real.stderr
    assert not (tmp_path / "out").exists()
