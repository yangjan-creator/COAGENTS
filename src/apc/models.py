from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WorkItem(Base):
    __tablename__ = "work_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))  # SUBPROJECT | FEATURE | TASK
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    owner_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("work_versions.id", use_alter=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WorkVersion(Base):
    __tablename__ = "work_versions"
    __table_args__ = (UniqueConstraint("work_item_id", "ordinal", name="uq_work_version_ordinal"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32), default="DRAFT")
    change_note: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ValidationGate(Base):
    __tablename__ = "validation_gates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    work_version_id: Mapped[str] = mapped_column(ForeignKey("work_versions.id"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    evidence_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    """Append-only history. Current-state tables never replace this evidence."""

    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"), nullable=True, index=True)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("work_versions.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class ProjectOverviewRevision(Base):
    __tablename__ = "project_overview_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    body_markdown: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PMSummaryEntry(Base):
    __tablename__ = "pm_summary_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    author: Mapped[str] = mapped_column(String(128))
    body_markdown: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Artifact(Base):
    """A registry entry, never an implicit copy of a large artifact."""

    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    path: Mapped[str] = mapped_column(String(2000), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    bytes: Mapped[int] = mapped_column(BigInteger)
    media_type: Mapped[str] = mapped_column(String(120))
    owner_actor: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str] = mapped_column(String(80))
    # UNIQUE_INPUT | ROLLBACK_POINT | VERIFIED_EPHEMERAL | EVIDENCE | DELETED
    retention_state: Mapped[str] = mapped_column(String(32), default="EVIDENCE")
    source_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ArtifactReference(Base):
    __tablename__ = "artifact_references"
    __table_args__ = (UniqueConstraint("artifact_id", "ref_kind", "ref_id", name="uq_artifact_ref"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    ref_kind: Mapped[str] = mapped_column(String(32))  # VERSION | GATE | SUMMARY
    ref_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DashboardTemplate(Base):
    __tablename__ = "dashboard_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    current_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("dashboard_template_revisions.id", use_alter=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DashboardTemplateRevision(Base):
    __tablename__ = "dashboard_template_revisions"
    __table_args__ = (UniqueConstraint("template_id", "ordinal", name="uq_dashboard_template_revision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("dashboard_templates.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    # JSON layout: widgets, columns, filters, and their field bindings.
    layout: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
