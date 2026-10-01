"""Download the ABIDE Preprocessed phenotypic file.

The URL pattern is taken from nilearn.datasets.fetch_abide_pcp (nilearn 0.14.1),
which is the reference implementation for accessing this dataset.

Only the phenotypic CSV is downloaded here. It is a small text file.
The region time series derivatives (rois_*) are also small text files with a
.1D extension. Everything else in the dataset, including func_preproc, is a
.nii.gz volume and is very large. Never request those.
"""

from __future__ import annotations

from pathlib import Path

import requests

CHUNK = 1 << 16


def phenotypic_url(base_url: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/{filename}"


def download(url: str, destination: Path, timeout: int = 120) -> Path:
    """Stream a file to disk, writing to a temporary name until complete."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with partial.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=CHUNK):
                if chunk:
                    fh.write(chunk)

    partial.replace(destination)
    return destination


VALID_PIPELINES = ("ccs", "cpac", "dparsf", "niak")
VALID_STRATEGIES = ("filt_global", "filt_noglobal", "nofilt_global", "nofilt_noglobal")


def parse_strategy(strategy: str) -> dict[str, bool]:
    """Turn a strategy string into the two flags nilearn expects.

    nilearn builds the strategy string as:
        ("no" if not band_pass else "") + "filt_" + ("no" if not global else "") + "global"

    Naive substring checks get this wrong, because "filt" is a substring of
    "nofilt" and "global" is a substring of "noglobal".
    """
    if strategy not in VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy {strategy!r}. Expected one of {VALID_STRATEGIES}.")
    return {
        "band_pass_filtering": not strategy.startswith("nofilt"),
        "global_signal_regression": "noglobal" not in strategy,
    }


def derivative_url(base_url: str, pipeline: str, strategy: str, derivative: str,
                   file_id: str) -> str:
    """Build the URL of one participant's derivative file.

    Layout confirmed against nilearn.datasets.fetch_abide_pcp, version 0.14.1:
        {base}/Outputs/{pipeline}/{strategy}/{derivative}/{FILE_ID}_{derivative}{ext}
    """
    ext = ".1D" if derivative.startswith("rois") else ".nii.gz"
    return (
        f"{base_url.rstrip('/')}/Outputs/{pipeline}/{strategy}/"
        f"{derivative}/{file_id}_{derivative}{ext}"
    )
