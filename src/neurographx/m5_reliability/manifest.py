"""Reliability grid manifests (M5 skeleton; memo 0016).

A reliability grid asks how much a result moves when one thing changes. Each job in the
grid changes exactly one thing, called its axis, from a fixed reference setting:

- ``atlas``     the reference run itself, once per atlas (its seed, all its folds);
- ``seed``      the same data and folds, another random seed;
- ``resample``  another training sample: a stratified bootstrap of the development pool,
                evaluated on the participants the bootstrap left out;
- ``site``      one imaging site left out of training and used as the evaluation set,
                which is how a model meets data from a scanner it never saw (memo 0015).

A job is the four values the work plan names: ``axis``, ``value``, ``atlas``, ``seed``.
The manifest is the full list of jobs, expanded from a small YAML grid definition. Its
identifier is a hash of the definition, and every job identifier is a hash of the
manifest identifier and the job's four values, so the same definition always gives the
same jobs. That is what lets the runner resume: a job whose identifier is already in the
run log is done.

A manifest never changes once written: a different definition under the same name is
refused, because the runs already logged would no longer match it. A new grid gets a new
name.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

AXES = ("atlas", "seed", "resample", "site")
SETTINGS = ("density", "fill_nan", "hidden", "layers", "dropout", "lr", "batch_size",
            "epochs", "class_weighted")


class ManifestError(ValueError):
    """The grid definition is invalid, or conflicts with a manifest already written."""


@dataclass(frozen=True)
class Job:
    job_id: str
    axis: str
    value: str | int
    atlas: str      # connectome key, for example rois_cc200
    seed: int

    def label(self) -> str:
        what = {"atlas": "reference run", "seed": f"seed {self.value}",
                "resample": f"resample {self.value}",
                "site": f"site {self.value} left out"}[self.axis]
        return f"{self.atlas}: {what}" + ("" if self.axis == "seed" else f" (seed {self.seed})")


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def job_id(manifest_id: str, axis: str, value, atlas: str, seed: int) -> str:
    return _hash([manifest_id, axis, value, atlas, seed])


def load_spec(path: Path) -> dict:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ManifestError(f"{path} does not hold a grid definition")
    return spec


def validate_spec(spec: dict, sites: list[str] | None = None) -> None:
    """Check a grid definition. `sites`: the development pool's sites, for the site axis."""
    for key in ("name", "atlases", "base_seed", "axes", "settings"):
        if key not in spec:
            raise ManifestError(f"the grid definition has no '{key}'")
    if not spec["atlases"]:
        raise ManifestError("the grid lists no atlas")
    unknown = sorted(set(spec["axes"]) - set(AXES))
    if unknown:
        raise ManifestError(f"unknown axis {unknown}; the axes are {', '.join(AXES)}")
    missing = [k for k in SETTINGS if k not in spec["settings"]]
    if missing:
        raise ManifestError(f"the settings lack {missing}")
    axes = spec["axes"]
    if "seed" in axes and (not isinstance(axes["seed"], list) or not axes["seed"]):
        raise ManifestError("the seed axis needs a list of seeds")
    if "resample" in axes and (not isinstance(axes["resample"], int) or axes["resample"] < 1):
        raise ManifestError("the resample axis needs a number of resamples (1 or more)")
    if "site" in axes and sites is not None and axes["site"] != "all":
        unknown_sites = sorted(set(axes["site"]) - set(sites))
        if unknown_sites:
            raise ManifestError(f"sites not in the development pool: {unknown_sites}")


def expand(spec: dict, sites: list[str]) -> dict:
    """The manifest of a grid definition: its identifier and every job, in a fixed order."""
    validate_spec(spec, sites)
    manifest_id = _hash(spec)
    base, axes = int(spec["base_seed"]), spec["axes"]
    jobs: list[Job] = []

    def add(axis, value, atlas, seed):
        jobs.append(Job(job_id(manifest_id, axis, value, atlas, seed), axis, value, atlas,
                        int(seed)))

    for atlas in spec["atlases"]:
        if axes.get("atlas"):
            add("atlas", atlas, atlas, base)
        for seed in axes.get("seed", []):
            add("seed", int(seed), atlas, int(seed))
        for i in range(axes.get("resample", 0)):
            add("resample", i, atlas, base)
        if "site" in axes:
            chosen = sorted(sites) if axes["site"] == "all" else list(axes["site"])
            for site in chosen:
                add("site", site, atlas, base)
    ids = [j.job_id for j in jobs]
    if len(set(ids)) != len(ids):
        raise ManifestError("the grid repeats a job (same axis, value, atlas and seed)")
    return {"name": spec["name"], "manifest_id": manifest_id, "spec": spec,
            "jobs": [asdict(j) for j in jobs]}


def jobs_of(manifest: dict) -> list[Job]:
    return [Job(**j) for j in manifest["jobs"]]


def manifest_path(out_dir: Path, name: str) -> Path:
    return grid_dir(out_dir, name) / "manifest.json"


def grid_dir(out_dir: Path, name: str) -> Path:
    """Where a grid's manifest and per-job prediction files go: runs/reliability/<name>/."""
    return Path(out_dir) / "runs" / "reliability" / name


def write_manifest(manifest: dict, out_dir: Path) -> Path:
    """Write the manifest once; writing the same one again is a no-op.

    Raises ManifestError if a different manifest already has this name.
    """
    path = manifest_path(out_dir, manifest["name"])
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("manifest_id") != manifest["manifest_id"]:
            raise ManifestError(
                f"grid '{manifest['name']}' already exists with another definition "
                f"(manifest {existing.get('manifest_id')}); give the new grid a new name")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
