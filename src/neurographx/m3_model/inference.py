"""Inference path (L7): participant in, prediction plus confidence out.

    predict("0050003", "cc200", get_graph)
    -> {"participant_id": "0050003", "atlas": "cc200", "prediction": "autism",
        "confidence": 0.73, "calibrated": False, "run_id": "85bd9bb6"}

The model is chosen through the model registry, never by file name, so the
answer always states which training run produced it (`run_id`).

No labels are read here and nothing is tuned: this module only applies an
already-selected checkpoint. It is safe to call on frozen-set participants.
"""
from collections.abc import Callable
from pathlib import Path

import torch

from neurographx import datasource
from neurographx.m3_model.model import model_from_checkpoint
from neurographx.m3_model.run_logger import REGISTRY_PATH, get_model

# Our own label coding (participant-record contract): 1 = autism, 0 = control.
LABELS = {0: "control", 1: "autism"}


def checkpoint_path(entry: dict, registry_path: Path = REGISTRY_PATH) -> Path:
    """Where the registered checkpoint is on this machine.

    Registry paths are relative ("checkpoints/cc200_00252f2b.pt"). A registry kept in a
    data root's ``runs/`` folder (the real one, or ``fixtures/runs/``) resolves them
    against that root through ``datasource.checkpoint`` (memo 0009), so the result does
    not depend on the working directory. Any other registry keeps the old behaviour:
    relative to the working directory. Absolute paths are returned unchanged.
    """
    registry_path = Path(registry_path)
    root = registry_path.parent.parent if registry_path.parent.name == "runs" else Path(".")
    return datasource.checkpoint(entry["checkpoint_path"], root=root)


def load_model(atlas: str, registry_path: Path = REGISTRY_PATH, device="cpu"):
    """Return (model, registry_entry) for the current model of `atlas`.

    The checkpoint is loaded onto `device` (CPU by default), so serving needs no GPU
    (memo 0009). Raises KeyError if no model is registered for the atlas, and
    FileNotFoundError if the registered checkpoint file is missing.
    """
    entry = get_model(atlas, registry_path)
    ckpt_path = checkpoint_path(entry, registry_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"checkpoint for atlas '{atlas}' (run {entry['run_id']}) not found: {ckpt_path}"
        )
    ckpt = torch.load(ckpt_path, map_location=device)
    model = model_from_checkpoint(ckpt).to(device)
    model.eval()  # dropout off: the same input always gives the same output
    return model, entry


@torch.no_grad()
def predict_graph(model, graph, device="cpu") -> tuple[int, float]:
    """Class index and softmax probability of that class for ONE graph."""
    in_dim = model.convs[0].in_channels
    if graph.x.ndim != 2 or graph.x.shape[1] != in_dim:
        raise ValueError(
            f"graph has feature shape {tuple(graph.x.shape)} but the model expects "
            f"{in_dim} features per node (wrong atlas for this model?)"
        )
    if not torch.isfinite(graph.x).all():
        raise ValueError("graph features contain NaN or inf")
    graph = graph.to(device)
    batch = torch.zeros(graph.x.shape[0], dtype=torch.long, device=device)
    logits = model(graph.x, graph.edge_index, batch)
    probs = torch.softmax(logits, dim=1)[0]
    label = int(probs.argmax())
    return label, float(probs[label])


def predict(participant_id: str, atlas: str, get_graph: Callable,
            registry_path: Path = REGISTRY_PATH, device="cpu") -> dict:
    """Prediction-response contract for one participant.

    `get_graph(participant_id)` must return that participant's graph for
    `atlas`, and raise KeyError for an unknown participant. The data loader
    supplies it; keeping it a parameter means this function is the same for
    synthetic graphs, real ABIDE graphs and the REST API.
    """
    model, entry = load_model(atlas, registry_path, device)
    graph = get_graph(participant_id)
    label, confidence = predict_graph(model, graph, device)
    return {
        "participant_id": participant_id,
        "atlas": atlas,
        "prediction": LABELS[label],
        "confidence": round(confidence, 4),
        "calibrated": False,  # raw softmax until calibration (after the midterm)
        "run_id": entry["run_id"],
    }
