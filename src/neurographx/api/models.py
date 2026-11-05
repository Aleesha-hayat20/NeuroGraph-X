"""Model endpoints (memo 0013, part 3; W5-10): what the registry serves, per atlas.

    GET /models             every registered model, one per atlas (memo 0004)
    GET /models/{atlas}     one atlas: 422 for an unknown atlas name, 503 if none registered

Each entry is the registry entry plus what a reader needs to judge it: the training
run's settings from the run log, whether the checkpoint file is on this machine, and
the calibration of memo 0010 when it exists. Read-only: nothing here loads a model or
reads the frozen set, so it needs no PyTorch. Works in fixture mode (memo 0014) through
`datasource`.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from neurographx import datasource
from neurographx.m3_model.run_logger import get_run, read_registry

router = APIRouter(tags=["models"])

# The four atlases of memo 0001, by the short name the registry and the API use.
ATLASES = ("aal", "cc200", "ho", "dosenbach160")


class ModelInfo(BaseModel):
    atlas: str
    run_id: str
    registered_at: str | None
    previous_run_ids: list[str]
    checkpoint_path: str
    checkpoint_available: bool
    hyperparameters: dict[str, Any] | None   # from the training run in the run log
    graph: dict[str, Any] | None             # atlas_key, density, fill_nan
    metrics: dict[str, Any]                  # as registered: frozen set and CV summary
    calibrated: bool                         # memo 0010: a calibration file exists
    calibration: dict[str, Any] | None


def calibration_file(atlas: str, run_id: str):
    """runs/calibration/<atlas>_<run_id>.json under the active data root (memo 0010)."""
    return datasource.data_root() / "runs" / "calibration" / f"{atlas}_{run_id}.json"


def model_info(atlas: str, entry: dict) -> dict:
    run = get_run(entry["run_id"], datasource.run_log()) or {}
    cfg = run.get("data_config") or {}
    cal_path = calibration_file(atlas, entry["run_id"])
    calibration = json.loads(cal_path.read_text(encoding="utf-8")) if cal_path.exists() else None
    return {
        "atlas": atlas,
        "run_id": entry["run_id"],
        "registered_at": entry.get("registered_at"),
        "previous_run_ids": list(entry.get("previous_run_ids", [])),
        "checkpoint_path": entry["checkpoint_path"],
        "checkpoint_available": datasource.checkpoint(entry["checkpoint_path"]).exists(),
        "hyperparameters": run.get("hyperparameters"),
        "graph": {k: cfg[k] for k in ("atlas_key", "density", "fill_nan") if k in cfg} or None,
        "metrics": entry.get("metrics") or {},
        "calibrated": calibration is not None,
        "calibration": calibration,
    }


@router.get("/models", response_model=list[ModelInfo], summary="Registered models")
def list_models() -> list[dict]:
    registry = read_registry(datasource.model_registry())
    return [model_info(atlas, registry[atlas]) for atlas in ATLASES if atlas in registry]


@router.get(
    "/models/{atlas}",
    response_model=ModelInfo,
    summary="The registered model of one atlas",
    responses={422: {"description": "Unknown atlas"},
               503: {"description": "No model registered for the atlas"}},
)
def get_model_info(atlas: str) -> dict:
    if atlas not in ATLASES:
        raise HTTPException(status_code=422,
                            detail=f"Unknown atlas '{atlas}'. Use one of: {', '.join(ATLASES)}")
    registry = read_registry(datasource.model_registry())
    if atlas not in registry:
        raise HTTPException(status_code=503,
                            detail=f"No model is registered for atlas '{atlas}'")
    return model_info(atlas, registry[atlas])
