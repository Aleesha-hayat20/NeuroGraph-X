"""Tests for the four-atlas ensemble (memo 0017).

The end-to-end tests use a copy of the synthetic fixture, extended to four members by
copying its one final run with shifted probabilities. No test computes the ensemble on the
real frozen set: that is the single measurement of memo 0017, run by hand once.
"""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from neurographx.m3_model import ensemble as ens
from neurographx.m3_model.run_logger import read_runs
from neurographx.utils.paths import project_root

ROOT = project_root()


def _load_script():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ensemble_script",
                                                  ROOT / "scripts/ensemble.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------

def test_combine_is_the_equal_weight_mean():
    probs = np.array([[0.9, 0.7, 0.2, 0.4], [0.1, 0.2, 0.3, 0.4]])
    assert ens.combine(probs) == pytest.approx([0.55, 0.25])


@pytest.mark.parametrize("bad", [np.array([[0.2, np.nan]]), np.array([[1.2, 0.3]]),
                                 np.array([0.2, 0.3]), np.zeros((3, 0))])
def test_combine_refuses_bad_probabilities(bad):
    with pytest.raises(ValueError):
        ens.combine(bad)


def test_threshold_is_inclusive_at_one_half():
    m = ens.scores([1, 0], [0.5, 0.4999])
    assert m["confusion_tn_fp_fn_tp"] == [1, 0, 0, 1]
    assert m["accuracy"] == 1.0 and m["predicted_autism"] == 1


def test_scores_match_the_single_model_record():
    y = [0, 0, 1, 1, 1]
    m = ens.scores(y, [0.1, 0.6, 0.7, 0.4, 0.9])
    assert set(m) == {"n", "accuracy", "accuracy_ci95_wilson", "balanced_accuracy", "auc",
                      "majority_baseline", "confusion_tn_fp_fn_tp", "predicted_autism"}
    assert m["accuracy"] == 0.6 and m["confusion_tn_fp_fn_tp"] == [1, 1, 1, 2]
    lo, hi = m["accuracy_ci95_wilson"]
    assert lo < 0.6 < hi


def test_wilson_interval_for_65_of_100():
    lo, hi = ens.wilson(65, 100)
    assert (round(lo, 2), round(hi, 2)) == (0.55, 0.74)  # as on the AAL model card


def test_members_must_agree_on_participants_and_labels():
    a = pd.DataFrame({"SUB_ID": [1, 2], "label": [0, 1], "prob_autism": [0.2, 0.8]})
    with pytest.raises(ValueError, match="participants differ"):
        ens._merge({"a": a, "b": a.assign(SUB_ID=[1, 3])})
    with pytest.raises(ValueError, match="labels differ"):
        ens._merge({"a": a, "b": a.assign(label=[1, 1])})
    with pytest.raises(ValueError, match="more than once"):
        ens._merge({"a": pd.concat([a, a])})


def test_registry_must_serve_the_runs_the_memo_names():
    registry = {a: {"run_id": r} for a, r in ens.MEMBERS.items()}
    ens.check_members(registry)
    registry["cc200"] = {"run_id": "00252f2b"}
    with pytest.raises(ValueError, match="new memo"):
        ens.check_members(registry)


def test_memo_members_are_the_registered_final_runs():
    registry = json.loads((ROOT / "runs/model_registry.json").read_text())
    assert {a: e["run_id"] for a, e in registry.items()} == ens.MEMBERS


def test_cv_evidence_reproduces_memo_0017():
    """Section 2 of the memo, from the committed out-of-fold files (development only)."""
    cv = ens.cv_evidence(ROOT)
    assert cv["n"] == 761
    got = {k: (cv["ensemble"][k]["mean"], cv["ensemble"][k]["sd"])
           for k in ("accuracy", "balanced_accuracy", "auc")}
    assert got == {"accuracy": pytest.approx((0.695, 0.020), abs=6e-4),
                   "balanced_accuracy": pytest.approx((0.687, 0.018), abs=6e-4),
                   "auc": pytest.approx((0.750, 0.037), abs=6e-4)}
    assert cv["aal"]["accuracy"]["mean"] == pytest.approx(0.6872, abs=1e-4)


# ---------------------------------------------------------------------------
# The script, end to end on the fixture extended to four members
# ---------------------------------------------------------------------------

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# The four_members fixture is in tests/conftest.py (shared with test_api_models.py).


def test_default_mode_checks_and_measures_nothing(four_members, capsys):
    root, members = four_members
    before = (root / "runs/run_log.jsonl").read_bytes()
    assert _load_script().main([], root=root, members=members) == 0
    assert "No metric was computed" in capsys.readouterr().out
    assert (root / "runs/run_log.jsonl").read_bytes() == before
    assert not list((root / "runs/frozen_predictions").glob("ensemble_*"))


def test_cv_mode_reads_no_frozen_file(four_members, monkeypatch):
    root, members = four_members
    script = _load_script()
    monkeypatch.setattr(script, "load_frozen_members",
                        lambda *a, **k: pytest.fail("--cv must not read the frozen set"))
    assert script.main(["--cv"], root=root, members=members) == 0


def _ensemble_records(root):
    return ens.read_ensemble_log(root / "runs/ensemble_log.jsonl")


def test_measure_once_records_one_measurement_and_refuses_a_second(four_members):
    root, members = four_members
    run_log_before = (root / "runs/run_log.jsonl").read_bytes()
    script = _load_script()
    assert script.main(["--measure-once"], root=root, members=members) == 0

    records = _ensemble_records(root)
    assert len(records) == 1
    rec = records[0]
    assert set(ens.REQUIRED) <= set(rec)
    assert rec["members"] == {a: members[a] for a in ("aal", "cc200", "ho", "dosenbach160")}
    assert rec["rule"]["threshold"] == 0.5 and rec["rule"]["memo"] == "0017"
    path = root / rec["predictions"]["file"]
    assert _sha(path) == rec["predictions"]["sha256"]

    out = pd.read_csv(path)
    member_cols = [f"prob_{a}" for a in ("aal", "cc200", "ho", "dosenbach160")]
    assert np.allclose(out["prob_autism"], out[member_cols].mean(axis=1), atol=1e-6)
    assert (out["prediction"] == (out["prob_autism"] >= 0.5)).all()
    assert rec["metrics"]["frozen"]["n"] == len(out)
    assert (root / "docs/reports/ensemble.md").read_text().startswith("# The four-atlas")
    # the run log, which holds training runs only (memo 0008), is not touched
    assert (root / "runs/run_log.jsonl").read_bytes() == run_log_before

    with pytest.raises(SystemExit, match="measured once"):
        script.main(["--measure-once"], root=root, members=members)
    assert len(_ensemble_records(root)) == 1


def test_build_db_still_imports_everything_after_a_measurement(four_members, tmp_path):
    """Aleesha's review of #208: the measurement must not break scripts/build_db.py."""
    import importlib.util
    root, members = four_members
    assert _load_script().main(["--measure-once"], root=root, members=members) == 0
    spec = importlib.util.spec_from_file_location("build_db", ROOT / "scripts/build_db.py")
    build_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_db)
    counts = build_db.build(root, tmp_path / "check.sqlite")
    assert counts["run_log"] == len(read_runs(root / "runs/run_log.jsonl"))


def _section8(root):
    from neurographx.integrity import check
    report = check(root, "fixtures", replay=False)
    return [f for f in report.findings if f.section == "8. Ensemble log"]


def test_integrity_passes_without_and_with_a_measurement(four_members):
    root, members = four_members
    assert [f.status for f in _section8(root)] == ["PASS"]
    assert _load_script().main(["--measure-once"], root=root, members=members) == 0
    found = _section8(root)
    assert [f.status for f in found] == ["PASS"], [f.message for f in found]


def test_integrity_fails_on_a_changed_ensemble_file_or_a_second_record(four_members):
    root, members = four_members
    assert _load_script().main(["--measure-once"], root=root, members=members) == 0
    log = root / "runs/ensemble_log.jsonl"
    rec = _ensemble_records(root)[0]
    path = root / rec["predictions"]["file"]
    good = path.read_text()

    path.write_text(good.replace("0.", "0.9", 1))
    assert any("does not match its hash" in f.message for f in _section8(root))

    path.write_text(good)
    log.write_text(log.read_text() + json.dumps({**rec, "ensemble_id": "second"}) + "\n")
    assert any("allows one" in f.message for f in _section8(root))


def test_a_changed_prediction_file_is_refused(four_members):
    root, members = four_members
    path = root / "runs/frozen_predictions/aal_fake1_frozen.csv"
    path.write_text(path.read_text().replace("0.", "0.1", 1))
    with pytest.raises(ValueError, match="differs from the hash"):
        _load_script().main(["--measure-once"], root=root, members=members)
    assert not _ensemble_records(root)


def test_crlf_copies_of_prediction_files_are_accepted(four_members):
    """A Windows checkout with CRLF endings holds the same predictions (memo 0010 files)."""
    root, members = four_members
    path = root / "runs/frozen_predictions/aal_fake1_frozen.csv"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert _load_script().main([], root=root, members=members) == 0
