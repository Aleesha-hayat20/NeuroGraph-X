"""Shapes of what the API returns (decision memo 0013). FastAPI checks every response
against these, and the OpenAPI page at /docs is generated from them."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Group = Literal["autism", "control"]
QCStatus = Literal["included", "excluded"]
Gate = Literal["rater", "motion", "completeness"]
Split = Literal["frozen", "development"]
Atlas = Literal["aal", "cc200", "ho", "dosenbach160"]


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    participant_table_found: bool
    data_mode: Literal["real", "fixtures"]  # NGX_DATA, memo 0014; the dashboard shows it


class Participant(BaseModel):
    participant_id: str = Field(description="Zero-padded ABIDE SUB_ID, 7 digits")
    file_id: str | None
    site: str | None
    group: Group | None
    sex: Literal["male", "female"] | None
    age: float | None
    qc_status: QCStatus
    exclusion_gate: Gate | None = Field(
        description="First quality-control gate failed (memo 0003); null when included")
    exclusion_reasons: list[str]
    split: Split | None = Field(
        description="frozen: the held-out evaluation set; development: used to train the "
                    "final models; null when excluded")


class ParticipantList(BaseModel):
    total: int = Field(description="Participants in the whole table, before filters")
    included: int = Field(description="Included in the whole table, before filters")
    excluded: int = Field(description="Excluded in the whole table, before filters")
    participants: list[Participant] = Field(description="The participants matching the filters")


class GroupCounts(BaseModel):
    included: int
    excluded: int


class SiteCounts(BaseModel):
    site: str
    included: int
    excluded: int


class CohortSummary(BaseModel):
    total: int
    included: int
    excluded: int
    excluded_by_gate: dict[Gate, int] = Field(
        description="Excluded participants counted at the first gate they failed")
    by_group: dict[Group, GroupCounts]
    by_site: list[SiteCounts]
    by_split: dict[Split, int] = Field(description="Included participants per split")


class Exclusion(BaseModel):
    participant_id: str
    file_id: str | None
    site: str | None
    group: Group | None
    first_gate_failed: Gate
    gates_failed: list[Gate]
    reasons: list[str]


class ExclusionList(BaseModel):
    total: int
    exclusions: list[Exclusion]


class AtlasInfo(BaseModel):
    atlas: str = Field(description="Short name used everywhere in the API, e.g. cc200")
    key: str = Field(description="ABIDE derivative key, e.g. rois_cc200")
    label: str
    family: str | None
    n_regions: int | None = Field(description="Graph nodes; null when the data is not available")
    data_available: bool
    model_registered: bool
    run_id: str | None = Field(description="Training run of the registered model, if any")


class AnalysisRecord(BaseModel):
    """One analysis: exactly the columns of analysis_log in db/schema.sql."""

    analysis_id: str = Field(description="12 lowercase hex characters")
    timestamp: str = Field(description="ISO 8601, UTC")
    participant_id: str
    atlas: Atlas
    run_id: str = Field(description="Training run whose model made the prediction")
    prediction: Group
    confidence: float = Field(ge=0.5, le=1.0,
                              description="Probability of the predicted class")
    calibrated: bool
    git_commit: str | None
    reproduces_analysis_id: str | None


class AnalysisRequest(BaseModel):
    """Body of POST /analyses. The atlas is checked by the endpoint (memo 0013, check 1),
    so an unknown name gets the documented sentence, not a schema error."""

    participant_id: str = Field(description="0050003 or 50003")
    atlas: str = Field(description="aal, cc200, ho or dosenbach160")


class AnalysisList(BaseModel):
    total: int = Field(description="Analyses matching the filters, before the limit")
    analyses: list[AnalysisRecord] = Field(description="Newest first")
