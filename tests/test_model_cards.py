"""scripts/make_model_cards.py on the fixture dataset: every number comes from the logs."""
import importlib.util
import json

from neurographx.utils.paths import project_root

spec = importlib.util.spec_from_file_location(
    "make_model_cards", project_root() / "scripts/make_model_cards.py")
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)


def test_wilson_interval_matches_the_cc200_baseline_report():
    lo, hi = mc.wilson(63, 100)  # 0.63 on the frozen 100: 0.532 to 0.718 (Week 2 report)
    assert (round(lo, 3), round(hi, 3)) == (0.532, 0.718)


def test_cards_and_table_are_built_from_the_fixture_logs(fixture_root, monkeypatch):
    monkeypatch.setattr(mc.datasource, "model_registry",
                        lambda root=None: fixture_root / "runs/model_registry.json")
    monkeypatch.setattr(mc.datasource, "run_log",
                        lambda root=None: fixture_root / "runs/run_log.jsonl")
    rows = mc.gather(None)
    assert [r["atlas"] for r in rows] == ["cc200"]
    final = rows[0]["final"]
    text = mc.card(rows[0])
    assert final["run_id"] in text and final["checkpoint_sha256"] in text
    assert f"{final['metrics']['frozen']['accuracy']:.3f}" in text
    assert "Not calibrated yet" in text and "Not a diagnostic" in text

    cal = fixture_root / f"runs/calibration/cc200_{final['run_id']}.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    scores = {"ece": 0.2, "brier": 0.25}
    cal.write_text(json.dumps({"method": "platt", "a": 0.3, "b": -0.1, "n": 12,
                               "oof": {"before": scores, "after_cross_fitted": scores},
                               "frozen": None}))
    text = mc.card(mc.gather(None)[0])
    assert "a = 0.3, b = -0.1" in text
    assert "| CC200 (200 regions) |" in mc.results_table(mc.gather(None))
