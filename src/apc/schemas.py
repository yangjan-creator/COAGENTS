from typing import Any

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    slug: str
    name: str
    actor: str


class ProjectCreate(BaseModel):
    team_id: str
    key: str
    name: str
    actor: str


class WorkItemCreate(BaseModel):
    key: str
    kind: str = Field(pattern="^(SUBPROJECT|FEATURE|TASK)$")
    title: str
    parent_id: str | None = None
    actor: str


class VersionCreate(BaseModel):
    change_note: str
    source_ref: str | None = None
    source_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    actor: str


class GateCreate(BaseModel):
    name: str
    required: bool = True
    actor: str


class GateResult(BaseModel):
    status: str = Field(pattern="^(PASSED|FAILED|WAIVED)$")
    evidence_uri: str | None = None
    evidence_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    actor: str
    message: str


class Claim(BaseModel):
    actor: str


class ProgressUpdate(BaseModel):
    actor: str
    message: str
    status: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class OverviewUpdate(BaseModel):
    actor: str
    body_markdown: str


class PMSummaryCreate(BaseModel):
    actor: str
    body_markdown: str
    evidence_refs: list[str] = Field(default_factory=list)


class ArtifactCreate(BaseModel):
    path: str
    sha256: str = Field(pattern="^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    media_type: str
    purpose: str = Field(pattern="^(UNIQUE_INPUT|ROLLBACK_POINT|VERIFIED_EPHEMERAL|EVIDENCE)$")
    source_ref: str | None = None
    actor: str


class ArtifactReferenceCreate(BaseModel):
    ref_kind: str = Field(pattern="^(VERSION|GATE|SUMMARY)$")
    ref_id: str
    actor: str


class DashboardTemplateCreate(BaseModel):
    name: str
    description: str = ""
    team_id: str | None = None
    project_id: str | None = None
    layout: dict
    actor: str


class DashboardTemplateRevisionCreate(BaseModel):
    layout: dict
    actor: str
