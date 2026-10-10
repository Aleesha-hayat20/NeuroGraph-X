"""Shapes of what the API returns. FastAPI checks every response against these."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    participant_table_found: bool


class Participant(BaseModel):
    participant_id: str
    file_id: str | None
    site: str | None
    group: Literal["autism", "control"] | None
    sex: Literal["male", "female"] | None
    age: float | None
    qc_status: Literal["included", "excluded"]
    exclusion_reasons: list[str]


class ParticipantList(BaseModel):
    total: int
    included: int
    excluded: int
    participants: list[Participant]
