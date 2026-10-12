"""ABIDE graphs for the GNN: stored connectomes (M2) in, PyG graphs out.

Reads the matrices through the connectome engine's interface (memo 0007) and
turns each participant into one graph with the same builder that the synthetic
test used (`matrix_to_graph`, memo 0006): node features are rows of the Fisher z
matrix, edges are the top `density` fraction of |z|.

Flat regions: memo 0007 stores them as NaN. They are filled with `fill_nan`
(0.0, "no connection measured") here, explicitly, so the choice is visible in
the run configuration. The graph builder still raises on any NaN that is left.
"""
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from neurographx.m2_connectome.engine import ConnectomeSet, atlas_paths, load_atlas
from neurographx.m3_model.synthetic_brain import matrix_to_graph

PIPELINE, STRATEGY = "cpac", "filt_global"  # memo 0002

# ABIDE DX_GROUP: 1 = autism, 2 = control. Our label: 1 = autism, 0 = control.
DX_TO_LABEL = {1: 1, 2: 0}


def short_atlas_name(atlas_key: str) -> str:
    """'rois_cc200' -> 'cc200', the name used by the registry, API and dashboard."""
    return atlas_key.removeprefix("rois_")


def labels_from_dx(dx: pd.Series) -> np.ndarray:
    unknown = set(dx.unique()) - set(DX_TO_LABEL)
    if unknown:
        raise ValueError(f"Unexpected DX_GROUP values: {sorted(unknown)}")
    return dx.map(DX_TO_LABEL).to_numpy(dtype=int)


def load_connectomes(connectome_dir: str | Path, atlas_key: str) -> ConnectomeSet:
    """Load one atlas file written by scripts/07_build_connectomes.py (hash-checked)."""
    npz, manifest = atlas_paths(Path(connectome_dir), PIPELINE, STRATEGY, atlas_key)
    if not npz.exists():
        raise FileNotFoundError(
            f"{npz} not found. Build it with scripts/07_build_connectomes.py, "
            "or point --connectomes at the folder holding the .npz and .json."
        )
    return load_atlas(npz, manifest)


def graph_for(cset: ConnectomeSet, participant, label: int | None = None,
              density: float = 0.10, fill_nan: float = 0.0):
    """One participant's graph. `participant` may be a FILE_ID, a SUB_ID or '0050003'."""
    i = cset.index(participant)
    z = cset.matrix(participant, kind="z", fill_nan=fill_nan)
    graph = matrix_to_graph(z, label=-1 if label is None else label, density=density,
                            subject_id=str(cset.file_ids[i]),
                            atlas=short_atlas_name(cset.atlas_key))
    graph.n_flat_regions = int(cset.zero_var[i].sum())
    return graph


def build_graphs(cset: ConnectomeSet, table: pd.DataFrame, density: float = 0.10,
                 fill_nan: float = 0.0) -> list:
    """Graphs for every row of a split table (needs FILE_ID, SITE_ID, DX_GROUP)."""
    labels = labels_from_dx(table["DX_GROUP"])
    graphs = []
    for file_id, site, label in zip(table["FILE_ID"], table["SITE_ID"], labels):
        g = graph_for(cset, file_id, int(label), density, fill_nan)
        g.site = str(site)
        graphs.append(g)
    return graphs


def flat_region_summary(cset: ConnectomeSet, table: pd.DataFrame) -> dict:
    """How many participants have flat (filled) regions, split by group.

    Flat regions follow the scanner's field of view, so they track site. If they
    also differ by group, the model could learn site instead of diagnosis.
    Call this on the development pool only, never on the frozen set.
    """
    counts = np.array([int(cset.zero_var[cset.index(f)].sum()) for f in table["FILE_ID"]])
    labels = labels_from_dx(table["DX_GROUP"])
    out = {}
    for name, value in (("autism", 1), ("control", 0)):
        c = counts[labels == value]
        out[name] = {"n": int(len(c)), "with_flat_regions": int((c > 0).sum()),
                     "mean_flat_regions": round(float(c.mean()), 3) if len(c) else 0.0}
    return out


def make_get_graph(cset: ConnectomeSet, density: float, fill_nan: float = 0.0) -> Callable:
    """The `get_graph` that inference.predict needs: participant id in, graph out.

    Unknown participants raise KeyError (the API turns that into a 404).
    """
    def get_graph(participant_id: str):
        return graph_for(cset, participant_id, None, density, fill_nan)
    return get_graph
