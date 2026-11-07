"""NeuroGraph-X REST API, the M3 service layer in the architecture (decision memo 0013).

Run locally:
    python -m uvicorn neurographx.api.main:app --reload
then open http://127.0.0.1:8000/docs

On the synthetic fixture dataset instead of the real data (memo 0014), one setting:
    NGX_DATA=fixtures python -m uvicorn neurographx.api.main:app --reload

Data side (this file):
    GET /health                              server up; data mode; participant table present
    GET /participants                        all participants; filters: site, group, qc_status
    GET /participants/{participant_id}       one participant
    GET /atlases                             the four atlases: size, data, registered model
    GET /cohort/summary                      counts for the Overview page
    GET /exclusions                          the exclusion log; filter: gate
    GET /analyses                            analysis history, newest first; filters
    GET /analyses/{analysis_id}              one analysis record

Model side (Laiba, api/models.py, W5-10):
    GET /models                              every registered model, one per atlas
    GET /models/{atlas}                      one atlas's model; 422 unknown atlas, 503 none

Model side (Laiba, api/analyses.py, W5-09):
    POST /analyses                           one analysis: checks of memo 0013 part 4 in
                                             order, prediction, record written; 201

Every error body is {"detail": "<plain sentence>"} (api/errors.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query

from neurographx import __version__, analysis_log, datasource
from neurographx.api import cohort, errors
from neurographx.api import participants as pt
from neurographx.api.analyses import run_analysis
from neurographx.api.models import router as models_router
from neurographx.api.schemas import (
    AnalysisList,
    AnalysisRecord,
    AnalysisRequest,
    AtlasInfo,
    CohortSummary,
    ExclusionList,
    Gate,
    Group,
    Health,
    Participant,
    ParticipantList,
    QCStatus,
)

datasource.mode()  # an unknown NGX_DATA value stops the server at start-up, not mid-demo

app = FastAPI(
    title="NeuroGraph-X API",
    version=__version__,
    description="Research use only. Not a diagnostic device, not a medical device.",
)
errors.install(app)
app.include_router(models_router)

NOT_FOUND = {404: {"description": "Unknown participant or analysis"}}
INVALID = {422: {"description": "Invalid filter or parameter value"}}
UNAVAILABLE = {503: {"description": "A data file is missing or inconsistent"}}


# ---------------------------------------------------------------------------
# Dependencies: which dataset this request reads. Tests replace get_root.
# ---------------------------------------------------------------------------

def get_root() -> Path:
    return datasource.data_root()


Root = Annotated[Path, Depends(get_root)]


def get_table_path(root: Root) -> Path:
    return pt.table_path(root)


TablePath = Annotated[Path, Depends(get_table_path)]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=Health, tags=["health"], summary="Server status")
def health(path: TablePath) -> dict:
    return {"status": "ok", "version": __version__, "participant_table_found": path.exists(),
            "data_mode": datasource.mode()}


# ---------------------------------------------------------------------------
# Participants (W5-03)
# ---------------------------------------------------------------------------

@app.get(
    "/participants",
    response_model=ParticipantList,
    tags=["participants"],
    summary="Participants with quality status",
    description="Counts cover the whole table; the list holds the participants matching every "
    "filter given. Quality status, gate and reasons come from the committed quality-control "
    "outputs (memo 0013).",
    responses={**INVALID, **UNAVAILABLE},
)
def list_participants(
    root: Root,
    site: str | None = Query(default=None, description="Imaging site, e.g. NYU"),
    group: Group | None = Query(default=None, description="autism or control"),
    qc_status: QCStatus | None = Query(default=None, description="included or excluded"),
) -> dict:
    records = pt.load_participants(root)
    if site is not None:
        sites = sorted({r["site"] for r in records if r["site"] is not None})
        canonical = {s.upper(): s for s in sites}
        if site.strip().upper() not in canonical:
            raise errors.unknown_value("site", site, sites)
        site = canonical[site.strip().upper()]
    shown = [r for r in records
             if (site is None or r["site"] == site)
             and (group is None or r["group"] == group)
             and (qc_status is None or r["qc_status"] == qc_status)]
    included = sum(r["qc_status"] == "included" for r in records)
    return {"total": len(records), "included": included, "excluded": len(records) - included,
            "participants": shown}


@app.get(
    "/participants/{participant_id}",
    response_model=Participant,
    tags=["participants"],
    summary="One participant",
    description="Accepts the 7-digit form (0050003) or the plain SUB_ID (50003).",
    responses={**NOT_FOUND, **UNAVAILABLE},
)
def get_participant(participant_id: str, root: Root) -> dict:
    record = pt.find_participant(pt.load_participants(root), participant_id)
    if record is None:
        raise errors.not_found("participant", participant_id)
    return record


# ---------------------------------------------------------------------------
# Atlases, cohort summary, exclusions (W5-02)
# ---------------------------------------------------------------------------

@app.get(
    "/atlases",
    response_model=list[AtlasInfo],
    tags=["atlases"],
    summary="The four atlases",
    description="Region count, whether connectome data is present, and whether a model is "
    "registered (with its training run).",
)
def list_atlases(root: Root) -> list[dict]:
    return cohort.atlas_records(root)


@app.get(
    "/cohort/summary",
    response_model=CohortSummary,
    tags=["cohort"],
    summary="Cohort counts for the Overview page",
    responses=UNAVAILABLE,
)
def cohort_summary(root: Root) -> dict:
    return cohort.summary(pt.load_participants(root))


@app.get(
    "/exclusions",
    response_model=ExclusionList,
    tags=["cohort"],
    summary="The exclusion log",
    description="Every participant excluded by quality control, with the first gate failed, "
    "every gate failed and every reason. `gate` keeps those whose first failed gate it is.",
    responses={**INVALID, **UNAVAILABLE},
)
def list_exclusions(
    root: Root,
    gate: Gate | None = Query(default=None, description="rater, motion or completeness"),
) -> dict:
    rows = cohort.exclusion_records(pt.load_participants(root), gate)
    return {"total": len(rows), "exclusions": rows}


# ---------------------------------------------------------------------------
# Analysis history (W5-07)
# ---------------------------------------------------------------------------

@app.get(
    "/analyses",
    response_model=AnalysisList,
    tags=["analyses"],
    summary="Analysis history, newest first",
    responses=INVALID,
)
def list_analyses(
    root: Root,
    participant_id: str | None = Query(default=None, description="0050003 or 50003"),
    atlas: str | None = Query(default=None, description="aal, cc200, ho or dosenbach160"),
    limit: int = Query(default=50, ge=1, le=1000, description="At most this many records"),
) -> dict:
    wanted = None
    if participant_id is not None:
        wanted = pt.normalise_id(participant_id)
        if wanted is None:
            raise errors.invalid(
                f"Invalid participant_id '{participant_id}': use the SUB_ID digits, "
                "for example 0050003 or 50003.")
    if atlas is not None and atlas not in cohort.atlas_names(root):
        raise errors.unknown_value("atlas", atlas, cohort.atlas_names(root))
    rows = analysis_log.read_analyses(datasource.analysis_log(root), wanted, atlas)
    return {"total": len(rows), "analyses": rows[:limit]}


@app.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisRecord,
    tags=["analyses"],
    summary="One analysis record",
    responses=NOT_FOUND,
)
def get_analysis(analysis_id: str, root: Root) -> dict:
    record = analysis_log.get_analysis(analysis_id, datasource.analysis_log(root))
    if record is None:
        raise errors.not_found("analysis", analysis_id)
    return record


@app.post(
    "/analyses",
    response_model=AnalysisRecord,
    status_code=201,
    tags=["analyses"],
    summary="Run one analysis and record it",
    responses={404: {"description": "Unknown participant"},
               409: {"description": "Participant excluded by quality control"},
               422: {"description": "Unknown atlas or invalid request body"},
               503: {"description": "No data, model or checkpoint for this atlas"}},
)
def create_analysis(request: AnalysisRequest, root: Root) -> dict:
    """Predict with the registered model of `atlas` and append the record to the analysis log.

    Research use only: the prediction is a model output for research, not a diagnosis.
    """
    return run_analysis(request.participant_id, request.atlas, root)
