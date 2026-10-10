"""Tests for run logging and the model registry (L5). No GPU libraries needed."""
import json

import pytest

from neurographx.m3_model.run_logger import (
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    get_model,
    get_run,
    log_run,
    new_run_id,
    read_runs,
    register_model,
)


def make_record(**overrides):
    record = {
        "run_id": new_run_id(),
        "dataset": "synthetic_brain",
        "atlas": "cc200",
        "seed": 42,
        "hyperparameters": {"hidden": 64, "layers": 3},
        "metrics": {"best_val_acc": 0.6},
        "checkpoint_path": "checkpoints/x.pt",
    }
    record.update(overrides)
    return record


def test_log_run_appends_one_valid_json_line_per_run(tmp_path):
    log = tmp_path / "runs" / "run_log.jsonl"
    first = log_run(make_record(), log)
    second = log_run(make_record(), log)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["run_id"] for line in lines] == [first, second]


def test_log_run_adds_provenance_fields(tmp_path):
    log = tmp_path / "run_log.jsonl"
    run_id = log_run(make_record(), log)
    saved = get_run(run_id, log)
    assert saved["schema_version"] == SCHEMA_VERSION
    assert saved["timestamp"].endswith("+00:00")
    assert "git_commit" in saved
    assert "python" in saved["environment"]


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_log_run_rejects_missing_required_field(tmp_path, field):
    log = tmp_path / "run_log.jsonl"
    record = make_record()
    del record[field]
    with pytest.raises(ValueError, match=field):
        log_run(record, log)
    assert not log.exists()  # nothing half-written


def test_log_run_rejects_duplicate_run_id(tmp_path):
    log = tmp_path / "run_log.jsonl"
    record = make_record()
    log_run(record, log)
    with pytest.raises(ValueError, match="already"):
        log_run(record, log)
    assert len(read_runs(log)) == 1


def test_unserialisable_record_writes_nothing(tmp_path):
    log = tmp_path / "run_log.jsonl"
    with pytest.raises(TypeError):
        log_run(make_record(metrics={"bad": object()}), log)
    assert not log.exists()


def test_old_records_without_schema_version_still_readable(tmp_path):
    log = tmp_path / "run_log.jsonl"
    log.write_text('{"run_id": "85bd9bb6", "dataset": "MUTAG", "atlas": null}\n')
    assert get_run("85bd9bb6", log)["dataset"] == "MUTAG"


def test_register_model_keeps_one_current_model_per_atlas(tmp_path):
    log, reg = tmp_path / "run_log.jsonl", tmp_path / "registry.json"
    first = log_run(make_record(), log)
    second = log_run(make_record(), log)
    other = log_run(make_record(atlas="aal"), log)
    register_model(first, log, reg)
    register_model(second, log, reg)
    register_model(other, log, reg)
    assert get_model("cc200", reg)["run_id"] == second
    assert get_model("cc200", reg)["previous_run_ids"] == [first]
    assert get_model("aal", reg)["run_id"] == other


def test_register_model_rejects_unlogged_run_and_missing_atlas(tmp_path):
    log, reg = tmp_path / "run_log.jsonl", tmp_path / "registry.json"
    with pytest.raises(ValueError, match="not in"):
        register_model("deadbeef", log, reg)
    toy = log_run(make_record(atlas=None), log)
    with pytest.raises(ValueError, match="no atlas"):
        register_model(toy, log, reg)
    with pytest.raises(KeyError):
        get_model("cc200", reg)
