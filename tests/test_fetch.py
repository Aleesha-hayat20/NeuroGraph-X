"""Strategy parsing and URL construction.

The strategy string is built by nilearn as
    ("no" if not band_pass else "") + "filt_" + ("no" if not global else "") + "global"
so naive substring checks are wrong: "filt" is inside "nofilt".
"""

from __future__ import annotations

import pytest

from neurographx.m1_ingestion.fetch import derivative_url, parse_strategy, phenotypic_url

BASE = "https://s3.amazonaws.com/fcp-indi/data/Projects/ABIDE_Initiative"


@pytest.mark.parametrize(
    "strategy,band_pass,global_signal",
    [
        ("filt_global", True, True),
        ("filt_noglobal", True, False),
        ("nofilt_global", False, True),
        ("nofilt_noglobal", False, False),
    ],
)
def test_parse_strategy(strategy, band_pass, global_signal):
    flags = parse_strategy(strategy)
    assert flags["band_pass_filtering"] is band_pass
    assert flags["global_signal_regression"] is global_signal


def test_parse_strategy_rejects_unknown():
    with pytest.raises(ValueError):
        parse_strategy("filtered_global")


def test_phenotypic_url():
    url = phenotypic_url(BASE, "Phenotypic_V1_0b_preprocessed1.csv")
    assert url == f"{BASE}/Phenotypic_V1_0b_preprocessed1.csv"


def test_roi_derivative_url_is_1d():
    url = derivative_url(BASE, "cpac", "filt_global", "rois_cc200", "UCLA_1_0051202")
    assert url.endswith("/rois_cc200/UCLA_1_0051202_rois_cc200.1D")
    assert "/Outputs/cpac/filt_global/" in url


def test_volume_derivative_url_is_niigz():
    url = derivative_url(BASE, "cpac", "filt_global", "func_preproc", "UCLA_1_0051202")
    assert url.endswith(".nii.gz")
