from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=128)


class TeamCreate(Command):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)


class MemberCreate(Command):
    member_actor: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["HUMAN", "AGENT"] = "AGENT"
    role: Literal["CONTRIBUTOR", "REVIEWER", "PM"] = "CONTRIBUTOR"
    team_id: str | None = None


class ProjectCreate(Command):
    team_id: str
    team_ids: list[str] = Field(default_factory=list)
    key: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=240)


class WorkItemCreate(Command):
    key: str = Field(min_length=1, max_length=64)
    kind: Literal["SUBPROJECT", "FEATURE", "TASK"] = "TASK"
    title: str = Field(min_length=1, max_length=500)
    parent_id: str | None = None
    description: str = ""
    team_id: str | None = None
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    labels: list[str] = Field(default_factory=list)


class VersionCreate(Command):
    change_note: str = Field(min_length=1)
    source_ref: str | None = None
    source_sha256: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")


class GateCreate(Command):
    name: str = Field(min_length=1, max_length=240)
    required: bool = True


class GateResult(Command):
    status: Literal["PASSED", "FAILED", "WAIVED"]
    evidence_uri: str = Field(min_length=1)
    evidence_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    message: str = Field(min_length=1)


class Claim(Command):
    pass


class ProgressUpdate(Command):
    message: str = Field(min_length=1)
    status: Literal["QUEUED", "WORKING", "READY_FOR_REVIEW", "VALIDATING", "BLOCKED", "HOLD", "PARKED"] | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkItemUpdate(Command):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] | None = None
    labels: list[str] | None = None


class DependencyCreate(Command):
    depends_on_id: str


class OverviewUpdate(Command):
    body_markdown: str = Field(min_length=1)


class PMSummaryCreate(Command):
    body_markdown: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class ArtifactCreate(Command):
    path: str = Field(min_length=1, max_length=2000)
    sha256: str = Field(pattern="^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    purpose: Literal["UNIQUE_INPUT", "ROLLBACK_POINT", "VERIFIED_EPHEMERAL", "EVIDENCE"]
    source_ref: str | None = None


class ArtifactReferenceCreate(Command):
    ref_kind: Literal["VERSION", "GATE", "SUMMARY"]
    ref_id: str


class ArtifactDeleted(Command):
    message: str = Field(min_length=1)


class Widget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["metric", "table", "board", "timeline", "summary", "artifacts"]
    title: str = Field(min_length=1, max_length=120)
    query: Literal["items", "blocked", "verified", "pending_gates", "events", "summaries", "artifacts"]
    columns: list[Literal["key", "title", "kind", "owner_actor", "status", "version", "progress", "team", "priority", "validation"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_binding(self):
        allowed = {
            "metric": {"items", "blocked", "verified", "pending_gates"},
            "table": {"items", "blocked", "verified"},
            "board": {"items"}, "timeline": {"events"},
            "summary": {"summaries"}, "artifacts": {"artifacts"},
        }
        if self.query not in allowed[self.type]:
            raise ValueError(f"{self.type} cannot render {self.query}")
        return self


class TemplateLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    widgets: list[Widget] = Field(min_length=1, max_length=20)
    statuses: list[str] = Field(default_factory=list)


class DashboardTemplateCreate(Command):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    team_id: str | None = None
    project_id: str | None = None
    layout: TemplateLayout

    @model_validator(mode="after")
    def one_scope(self):
        if self.team_id and self.project_id:
            raise ValueError("choose team or project scope, not both")
        return self


class DashboardTemplateRevisionCreate(Command):
    layout: TemplateLayout
