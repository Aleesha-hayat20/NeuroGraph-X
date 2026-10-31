"""Memo 0011: the declared grid, resumable runs, and the selection rule (no PyTorch needed)."""
import pytest

from neurographx.m3_model.tuning import (
    BASELINE,
    GRID,
    GRID_TAG,
    TIE_MARGIN,
    Config,
    pending,
    render,
    select,
    table,
)

BASE = Config(BASELINE["density"], BASELINE["class_weighted"], BASELINE["hidden"])


def run(run_id, config, balanced, sd=0.02, atlas="cc200", tag=GRID_TAG,
        when="2026-11-01T10:00:00+00:00", stage="cv", dataset="ABIDE"):
    data_config = {"density": config.density, "fill_nan": 0.0}
    if tag:
        data_config["tuning_grid"] = tag
    return {"run_id": run_id, "timestamp": when, "stage": stage, "dataset": dataset,
            "atlas": atlas, "data_config": data_config,
            "hyperparameters": {"hidden": config.hidden, "class_weighted": config.class_weighted},
            "metrics": {"cv_balanced_accuracy": {"mean": balanced, "sd": sd},
                        "cv_accuracy": {"mean": balanced + 0.01, "sd": sd},
                        "cv_auc": {"mean": 0.7, "sd": 0.03}, "chosen_epochs": 20}}


def full_grid(scores, **kw):
    return [run(f"r{i:02d}", c, scores.get(c, 0.60), **kw) for i, c in enumerate(GRID)]


def test_grid_is_the_declared_twelve_with_the_baseline_in_it():
    assert len(GRID) == 12 and len(set(GRID)) == 12
    assert BASE in GRID and BASE.changes() == 0
    assert {c.density for c in GRID} == {0.05, 0.10, 0.20}
    assert {c.hidden for c in GRID} == {32, 64}
    assert Config(0.2, True, 32).changes() == 3


def test_config_args_reproduce_the_configuration():
    assert Config(0.05, True, 32).args() == ["--density", "0.05", "--hidden", "32",
                                            "--class-weighted"]
    assert "--class-weighted" not in BASE.args()


def test_pending_skips_logged_configurations_and_untagged_runs():
    runs = [run("a", GRID[0], 0.6), run("b", GRID[1], 0.6, tag=None),
            run("c", GRID[2], 0.6, atlas="aal")]
    assert pending(runs, "cc200") == list(GRID[1:])
    assert len(pending([], "cc200")) == 12


def test_highest_balanced_accuracy_wins():
    best = Config(0.2, True, 64)
    rows = table(full_grid({best: 0.70}), "cc200")
    winner, tied = select(rows)
    assert winner.config == best and len(tied) == 1


def test_a_tie_goes_to_fewer_changes_from_the_baseline():
    near, far = Config(0.10, True, 64), Config(0.2, True, 32)
    rows = table(full_grid({far: 0.700, near: 0.700 - TIE_MARGIN / 2}), "cc200")
    winner, tied = select(rows)
    assert winner.config == near and {r.config for r in tied} == {near, far}


def test_still_tied_goes_to_the_lower_standard_deviation():
    a, b = Config(0.05, False, 64), Config(0.2, False, 64)  # one change each
    runs = full_grid({})
    for r in runs:
        if r["data_config"]["density"] == a.density and r["hyperparameters"]["hidden"] == 64 \
                and not r["hyperparameters"]["class_weighted"]:
            r["metrics"]["cv_balanced_accuracy"] = {"mean": 0.70, "sd": 0.03}
        if r["data_config"]["density"] == b.density and r["hyperparameters"]["hidden"] == 64 \
                and not r["hyperparameters"]["class_weighted"]:
            r["metrics"]["cv_balanced_accuracy"] = {"mean": 0.70, "sd": 0.01}
    winner, _ = select(table(runs, "cc200"))
    assert winner.config == b


def test_runs_after_the_freeze_and_duplicates_do_not_count():
    best = Config(0.05, True, 32)
    runs = full_grid({}) + [run("late", best, 0.90, when="2026-11-02T08:00:00+00:00"),
                            run("again", BASE, 0.95, when="2026-11-01T12:00:00+00:00")]
    rows = table(runs, "cc200")
    winner, _ = select(rows)
    assert winner.run["run_id"] not in {"late", "again"}
    by_config = {r.config: r for r in rows}
    assert by_config[BASE].run["run_id"] != "again" and by_config[BASE].ignored
    assert "after the freeze" in by_config[best].note


def test_other_atlases_stages_and_datasets_are_not_mixed_in():
    runs = [run("x", GRID[0], 0.9, atlas="aal"), run("y", GRID[0], 0.9, stage="final"),
            run("z", GRID[0], 0.9, dataset="synthetic_brain")]
    winner, tied = select(table(runs, "cc200"))
    assert winner is None and tied == []


def test_report_marks_the_winner_and_states_the_frozen_set_rule():
    rows = table(full_grid({Config(0.2, True, 64): 0.71}), "cc200")
    rows_aal = table(full_grid({}, atlas="aal"), "aal")
    text = render({"cc200": (rows, *select(rows)), "aal": (rows_aal, *select(rows_aal)),
                   "ho": (table([], "ho"), None, [])})
    assert text.count("**selected**") == 2
    assert "declared repeat" in text and "--allow-repeat" in text
    assert "optimistic" in text
    assert "nothing selected" in text


@pytest.mark.parametrize("winner_is_baseline", [True, False])
def test_cc200_frozen_rule_depends_on_whether_the_baseline_wins(winner_is_baseline):
    target = BASE if winner_is_baseline else Config(0.05, False, 64)
    rows = table(full_grid({target: 0.75}), "cc200")
    text = render({"cc200": (rows, *select(rows))})
    assert ("00252f2b` remains" in text) == winner_is_baseline
    assert ("--allow-repeat" in text) == (not winner_is_baseline)


def test_grid_runner_dry_run_lists_every_pending_configuration(tmp_path):
    import os
    import subprocess
    import sys

    from neurographx.utils.paths import project_root

    root = project_root()
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    done = subprocess.run([sys.executable, str(root / "scripts/run_tuning_grid.py"),
                           "--atlas", "all", "--dry-run"], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert "48 still to run" in done.stdout
    assert not (tmp_path / "runs").exists()  # a dry run writes nothing
