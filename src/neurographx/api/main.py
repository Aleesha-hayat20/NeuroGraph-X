"""NeuroGraph-X REST API skeleton (issue #21). The M3 service layer in the architecture.

Run locally:
    python -m uvicorn neurographx.api.main:app --reload
then open http://127.0.0.1:8000/docs

Endpoints:
    GET /health                          the server is up; is the participant table there
    GET /participants[?qc_status=...]    participant list with quality status and reasons
    GET /participants/{participant_id}   one participant
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query

from neurographx import __version__
from neurographx.api import participants as pt
from neurographx.api.schemas import Health, Participant, ParticipantList
from neurographx.m1_ingestion import screening

app = FastAPI(
    title="NeuroGraph-X API",
    version=__version__,
    description="Research use only. Not a diagnostic device.",
)


def get_table_path() -> Path:
    return pt.table_path()


def get_criteria() -> dict[str, list[str]]:
    return screening.rater_criteria()


TablePath = Annotated[Path, Depends(get_table_path)]
Criteria = Annotated[dict, Depends(get_criteria)]


def _participants(path: Path, criteria: dict) -> list[dict]:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Participant table {path.name} not found in data/raw. "
            "Run scripts/01_fetch_phenotypic.py first.",
        )
    try:
        return pt.load_participants(path, criteria)
    except ValueError as err:
        raise HTTPException(status_code=500, detail=f"Participant table unreadable: {err}")


@app.get("/health", response_model=Health, tags=["health"], summary="Server status")
def health(path: TablePath) -> dict:
    return {"status": "ok", "version": __version__, "participant_table_found": path.exists()}


@app.get(
    "/participants",
    response_model=ParticipantList,
    tags=["participants"],
    summary="Participant list with quality status",
    description="Counts cover the whole table; the list is filtered by qc_status if given. "
    "qc_status=excluded is the exclusion log view.",
)
def list_participants(
    path: TablePath,
    criteria: Criteria,
    qc_status: Literal["included", "excluded"] | None = Query(
        default=None, description="Only participants with this quality status."
    ),
) -> dict:
    records = _participants(path, criteria)
    included = sum(r["qc_status"] == "included" for r in records)
    shown = records if qc_status is None else [r for r in records if r["qc_status"] == qc_status]
    return {
        "total": len(records),
        "included": included,
        "excluded": len(records) - included,
        "participants": shown,
    }


@app.get(
    "/participants/{participant_id}",
    response_model=Participant,
    tags=["participants"],
    summary="One participant",
    responses={404: {"description": "Unknown participant"}},
)
def get_participant(participant_id: str, path: TablePath, criteria: Criteria) -> dict:
    records = _participants(path, criteria)
    wanted = pt.participant_id(participant_id) if participant_id.isdigit() else None
    for record in records:
        if record["participant_id"] == wanted:
            return record
    raise HTTPException(status_code=404, detail=f"Unknown participant: {participant_id}")

