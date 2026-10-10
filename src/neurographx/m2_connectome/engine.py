"""M2 connectome engine: region time series to stored, cached connectivity matrices.

One call per atlas turns every cohort participant's region time series into a
Pearson correlation matrix and its Fisher z transform, then stores the whole
atlas as one file. Running it again with the same inputs reuses the stored file.

Storage format (one pair of files per atlas, decision memo 0007):

    {output_dir}/{pipeline}_{strategy}/{atlas_key}.npz
        file_ids       (n,)        str     ABIDE FILE_ID, row order of every array
        sub_ids        (n,)        int64   ABIDE SUB_ID
        r_triu         (n, E)      float32 Pearson r, strict upper triangle
        z_triu         (n, E)      float32 Fisher z, strict upper triangle
        zero_var       (n, R)      bool    True where a region's signal is flat
        n_timepoints   (n,)        int32   length of each participant's time series

    {output_dir}/{pipeline}_{strategy}/{atlas_key}.json
        manifest: atlas, node count, edge count, parameters, engine version,
        the fingerprint of every input, and the SHA-256 of the .npz

R is the number of regions (graph nodes) and E = R (R - 1) / 2 the number of
edges. Only the upper triangle is stored because the matrix is symmetric and
its diagonal is fixed, which halves the size on disk. `ConnectomeSet.matrix`
rebuilds the full square matrix.

Caching: the fingerprint is a SHA-256 over the engine version, the parameters,
the ordered participant list and the content hash of every input .1D file. If
the stored manifest carries the same fingerprint and the .npz still matches its
recorded hash, nothing is recomputed. Any change to any input rebuilds.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from neurographx.m2_connectome import connectivity as cx

ENGINE_VERSION = "1.0.0"
_MEMO: dict[tuple[str, int], "ConnectomeSet"] = {}


# ---------------------------------------------------------------------------
# One participant
# ---------------------------------------------------------------------------

def compute_subject(ts: np.ndarray, clip: float = cx.DEFAULT_FISHER_CLIP,
                    dtype: str = "float32") -> dict:
    """Correlation, Fisher z and zero-variance mask for one (timepoints, regions) array."""
    ts = np.asarray(ts, dtype=np.float64)
    if ts.ndim != 2 or ts.shape[0] < 2:
        raise ValueError(f"Need at least two timepoints, got shape {ts.shape}")
    zero_var = np.zeros(ts.shape[1], dtype=bool)
    zero_var[cx.zero_variance_regions(ts)] = True
    r = cx.correlation_matrix(ts)
    report = cx.check_matrix(r, np.where(zero_var)[0])
    if not cx.is_valid(report):
        raise ValueError(f"Correlation matrix failed validity checks: {report}")
    z = cx.fisher_z(r, clip=clip)
    return {
        "r_triu": cx.to_triu(r).astype(dtype),
        "z_triu": cx.to_triu(z).astype(dtype),
        "zero_var": zero_var,
        "n_timepoints": ts.shape[0],
    }


# ---------------------------------------------------------------------------
# Hashing and fingerprints
# ---------------------------------------------------------------------------

def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def input_fingerprint(params: dict, file_ids: Iterable[str], paths: Iterable[Path]) -> str:
    """SHA-256 over parameters, participant order and input file contents."""
    h = hashlib.sha256()
    h.update(json.dumps({"engine_version": ENGINE_VERSION, **params}, sort_keys=True).encode())
    for fid, p in zip(file_ids, paths):
        h.update(fid.encode())
        h.update(sha256_file(p).encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Stored set for one atlas
# ---------------------------------------------------------------------------

@dataclass
class ConnectomeSet:
    """Every participant's connectome for one atlas, as loaded from disk."""

    atlas_key: str
    n_regions: int
    file_ids: np.ndarray
    sub_ids: np.ndarray
    r_triu: np.ndarray
    z_triu: np.ndarray
    zero_var: np.ndarray
    n_timepoints: np.ndarray
    manifest: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.file_ids)

    @property
    def n_edges(self) -> int:
        return self.r_triu.shape[1]

    def index(self, participant: str | int) -> int:
        """Row of a participant, given a FILE_ID ("NYU_0050952"), a SUB_ID (50952), or the
        zero-padded SUB_ID string the API and inference use ("0050952")."""
        if isinstance(participant, str) and participant.isdigit():
            participant = int(participant)
        if isinstance(participant, str):
            hits = np.flatnonzero(self.file_ids == participant)
        else:
            hits = np.flatnonzero(self.sub_ids == int(participant))
        if len(hits) != 1:
            raise KeyError(f"Participant {participant!r} is not in the {self.atlas_key} set")
        return int(hits[0])

    def edges(self, kind: str = "z") -> np.ndarray:
        """(n, E) edge vectors, the compact form a classical model would use."""
        if kind not in ("r", "z"):
            raise ValueError(f"kind must be 'r' or 'z', got {kind!r}")
        return self.r_triu if kind == "r" else self.z_triu

    def matrix(self, participant: str | int, kind: str = "z",
               fill_nan: float | None = None) -> np.ndarray:
        """Full square matrix for one participant.

        Diagonal: 1 for r and 0 for z. Rows and columns of zero-variance regions
        are NaN in both, including their diagonal entry for r, unless `fill_nan`
        is given, in which case every NaN is replaced by that value.
        """
        i = self.index(participant)
        diagonal = 1.0 if kind == "r" else 0.0
        m = cx.from_triu(self.edges(kind)[i], self.n_regions, diagonal)
        if kind == "r":
            zv = np.flatnonzero(self.zero_var[i])
            m[zv, zv] = np.nan
        if fill_nan is not None:
            m = np.where(np.isnan(m), np.asarray(fill_nan, dtype=m.dtype), m)
        return m

    def stack(self, kind: str = "z", fill_nan: float | None = None,
              participants: Iterable[str | int] | None = None) -> np.ndarray:
        """(n, R, R) array of full matrices, in file_ids order or the order given."""
        rows = range(len(self)) if participants is None else \
            [self.index(p) for p in participants]
        return np.stack([self.matrix(self.file_ids[i], kind, fill_nan) for i in rows])


def atlas_paths(output_dir: Path, pipeline: str, strategy: str,
                atlas_key: str) -> tuple[Path, Path]:
    folder = Path(output_dir) / f"{pipeline}_{strategy}"
    return folder / f"{atlas_key}.npz", folder / f"{atlas_key}.json"


def load_atlas(npz_path: Path, manifest_path: Path | None = None,
               verify_hash: bool = True) -> ConnectomeSet:
    """Load one stored atlas. Kept in memory per process, keyed by path and mtime."""
    npz_path = Path(npz_path)
    manifest_path = manifest_path or npz_path.with_suffix(".json")
    key = (str(npz_path.resolve()), npz_path.stat().st_mtime_ns)
    if key in _MEMO:
        return _MEMO[key]

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if verify_hash and sha256_file(npz_path) != manifest["output_sha256"]:
        raise ValueError(f"{npz_path} does not match the hash in its manifest. Rebuild it.")
    with np.load(npz_path, allow_pickle=False) as data:
        cset = ConnectomeSet(
            atlas_key=manifest["atlas_key"],
            n_regions=int(manifest["n_regions"]),
            file_ids=data["file_ids"].astype(str),
            sub_ids=data["sub_ids"],
            r_triu=data["r_triu"],
            z_triu=data["z_triu"],
            zero_var=data["zero_var"],
            n_timepoints=data["n_timepoints"],
            manifest=manifest,
        )
    _MEMO[key] = cset
    return cset


def _atomic_savez(path: Path, **arrays) -> None:
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez(tmp, **arrays)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Build one atlas
# ---------------------------------------------------------------------------

def build_atlas(atlas_key: str, cohort: pd.DataFrame, ts_folder: Path, output_dir: Path,
                pipeline: str, strategy: str, clip: float = cx.DEFAULT_FISHER_CLIP,
                dtype: str = "float32", force: bool = False, label: str | None = None,
                progress: Callable[[int, int], None] | None = None
                ) -> tuple[ConnectomeSet, str]:
    """Build (or reuse) the stored connectomes for one atlas.

    `cohort` needs FILE_ID and SUB_ID columns; its row order becomes the stored order.
    Returns the loaded set and "built" or "cached".
    """
    file_ids = [str(f) for f in cohort["FILE_ID"]]
    if len(set(file_ids)) != len(file_ids):
        raise ValueError("Duplicate FILE_ID in the cohort")
    paths = [Path(ts_folder) / f"{fid}_{atlas_key}.1D" for fid in file_ids]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} time series files missing, e.g. {missing[:3]}")

    params = {"atlas_key": atlas_key, "pipeline": pipeline, "strategy": strategy,
              "measure": "pearson", "fisher_clip": clip, "dtype": dtype, "storage": "triu_k1"}
    fingerprint = input_fingerprint(params, file_ids, paths)
    npz_path, manifest_path = atlas_paths(output_dir, pipeline, strategy, atlas_key)

    if not force and npz_path.exists() and manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("input_fingerprint") == fingerprint:
            try:
                return load_atlas(npz_path, manifest_path, verify_hash=True), "cached"
            except ValueError:
                pass  # stored file corrupted or edited, fall through and rebuild

    results = []
    for k, p in enumerate(paths, 1):
        results.append(compute_subject(cx.load_1d(p), clip=clip, dtype=dtype))
        if progress:
            progress(k, len(paths))

    regions = {len(r["zero_var"]) for r in results}
    if len(regions) != 1:
        raise ValueError(f"Inconsistent region counts within {atlas_key}: {sorted(regions)}")
    n_regions = regions.pop()

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_savez(
        npz_path,
        file_ids=np.array(file_ids),
        sub_ids=np.asarray(cohort["SUB_ID"], dtype=np.int64),
        r_triu=np.stack([r["r_triu"] for r in results]),
        z_triu=np.stack([r["z_triu"] for r in results]),
        zero_var=np.stack([r["zero_var"] for r in results]),
        n_timepoints=np.array([r["n_timepoints"] for r in results], dtype=np.int32),
    )
    zv = np.stack([r["zero_var"] for r in results])
    manifest = {
        "atlas_key": atlas_key,
        "atlas_label": label or atlas_key,
        "n_regions": int(n_regions),
        "n_edges": int(n_regions * (n_regions - 1) // 2),
        "n_participants": len(file_ids),
        "participants_with_zero_variance": int(zv.any(axis=1).sum()),
        "engine_version": ENGINE_VERSION,
        "parameters": params,
        "storage": {
            "format": "npz",
            "triangle": "strict upper, numpy.triu_indices(n_regions, k=1), row-major",
            "diagonal_r": 1.0,
            "diagonal_z": 0.0,
            "nan": "rows and columns of zero-variance regions, see zero_var",
        },
        "input_fingerprint": fingerprint,
        "output_sha256": sha256_file(npz_path),
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "numpy_version": np.__version__,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _MEMO.clear()
    return load_atlas(npz_path, manifest_path, verify_hash=False), "built"
