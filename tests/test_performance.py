"""Performance (#139, NFR-9): analysis time on the CPU, and repeated requests.

The fixture test runs everywhere, CI included: it checks that the benchmark works, that
repeated requests give the same answer, and that nothing reaches the analysis log. The
real-data test runs only where the real connectomes, participant table and checkpoints are
present (a team laptop, not CI), and checks NFR-9 there: every analysis after the first,
which also loads the atlas's connectomes, completes within 5 seconds. The numbers for the
report come from `python scripts/benchmark_api.py` (docs/reports/performance.md).
"""

from __future__ import annotations

import importlib.util
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx import datasource  # noqa: E402
from neurographx.utils.paths import project_root  # noqa: E402

ROOT = project_root()
spec = importlib.util.spec_from_file_location("benchmark_api", ROOT / "scripts/benchmark_api.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def _real_data_present() -> bool:
    registry_path = ROOT / "runs/model_registry.json"
    if not (ROOT / "data/raw/Phenotypic_V1_0b_preprocessed1.csv").exists():
        return False
    registry = json.loads(registry_path.read_text())
    connectomes = ROOT / "data/processed/connectomes/cpac_filt_global"
    return all((ROOT / e["checkpoint_path"]).exists()
               and (connectomes / f"rois_{a}.npz").exists() for a, e in registry.items())


def test_benchmark_on_fixtures_repeats_the_same_answer_quickly(monkeypatch):
    monkeypatch.setenv("NGX_DATA", "fixtures")
    log = datasource.analysis_log()
    before = log.read_bytes() if log.exists() else None
    rows = bench.benchmark(repeats=5)
    assert rows and all(r["identical"] and r["within_limit"] for r in rows)
    assert (log.read_bytes() if log.exists() else None) == before  # log untouched
    assert bench.table(rows, "0090001").count("| yes") == 2 * len(rows)


@pytest.mark.skipif(not _real_data_present(),
                    reason="real ABIDE data not present (team laptops only)")
def test_nfr9_on_real_data_every_analysis_within_five_seconds(monkeypatch):
    monkeypatch.delenv("NGX_DATA", raising=False)
    rows = {r["atlas"]: r for r in bench.benchmark(repeats=5)}
    assert set(rows) == {"aal", "cc200", "ho", "dosenbach160"}
    for atlas, r in rows.items():
        assert r["identical"], atlas
        assert r["warm_max_s"] <= bench.LIMIT_S, (atlas, r["warm_max_s"])
    # the same answer as manual check AC-06
    assert (rows["cc200"]["run_id"], rows["cc200"]["prediction"],
            rows["cc200"]["confidence"]) == ("cf60f29e", "control", 0.5124)
