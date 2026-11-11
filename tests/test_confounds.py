"""Confound check (src/neurographx/m3_model/confounds.py, scripts/confound_check.py).

The measures are checked on hand-made numbers; the whole analysis runs on a private copy
of the fixture dataset (memo 0014), whose numbers mean nothing but have the real formats.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from neurographx.m3_model.confounds import (
    QUARTILES,
    ConfoundInputError,
    analyse,
    render,
    scores,
    wilson_interval,
)
from neurographx.utils.paths import project_root


def test_scores_on_known_numbers():
    s = scores([1, 1, 0, 0], [1, 0, 0, 0])
    assert s["n"] == 4 and s["accuracy"] == 0.75
    assert s["balanced_accuracy"] == pytest.approx((0.5 + 1.0) / 2)
    assert s["autism_share"] == 0.5 and s["predicted_autism_share"] == 0.25


def test_balanced_accuracy_is_undefined_with_one_group():
    assert scores([1, 1], [1, 0])["balanced_accuracy"] is None
    assert scores([], [])["accuracy"] is None


def test_wilson_interval_matches_a_textbook_value():
    lo, hi = wilson_interval(13, 20)  # 0.65 at n = 20: about 0.433 to 0.819
    assert lo == pytest.approx(0.4329, abs=1e-3) and hi == pytest.approx(0.8188, abs=1e-3)
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_the_analysis_runs_on_the_fixture(fixture_root):
    result = analyse(fixture_root)
    assert list(result["atlases"]) == ["cc200"]  # the fixture registers one model
    cc = result["atlases"]["cc200"]
    assert cc["overall"]["n"] == result["n"] == 11  # the fixture's development pool
    assert sum(e["n"] for e in result["sites"]) == result["n"]
    assert [q["quartile"] for q in result["quartiles"]] == list(QUARTILES)
    assert sum(q["n"] for q in result["quartiles"]) == result["n"]
    groups = cc["flat"]["by_group"]
    assert groups["autism"]["n"] + groups["control"]["n"] == result["n"]
    assert cc["flat"]["with"]["n"] + cc["flat"]["without"]["n"] == result["n"]


def test_the_report_has_every_section_and_no_frozen_numbers(fixture_root):
    text = render(analyse(fixture_root), "2026-11-08", "the SYNTHETIC fixture data")
    for heading in ("## 1. Overall", "## 2. Accuracy by imaging site",
                    "## 3. Accuracy by head motion", "## 4. Flat regions by group",
                    "## How to read this", "## Limitations this supports in the report"):
        assert heading in text
    assert "limitation analysis" in text and "The frozen set is not read." in text


def test_a_changed_oof_file_stops_the_analysis(fixture_root):
    oof = next((fixture_root / "runs/oof").glob("*.csv"))
    oof.write_text(oof.read_text() + "\n")
    with pytest.raises(ConfoundInputError, match="does not match the run log"):
        analyse(fixture_root)


def test_the_script_prints_the_fixture_report_without_writing_it():
    root = project_root()
    out = subprocess.run([sys.executable, "scripts/confound_check.py", "--data", "fixtures"],
                         cwd=root, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "# Confound check on the out-of-fold predictions" in out.stdout
    assert "SYNTHETIC" in out.stdout
    assert not (root / "fixtures/docs/reports/confound_check.md").exists()
