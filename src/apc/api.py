from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from apc.db import SessionLocal, init_db
from apc.models import (
    Artifact,
    ArtifactReference,
    AuditEvent,
    DashboardTemplate,
    DashboardTemplateRevision,
    PMSummaryEntry,
    Project,
    ProjectOverviewRevision,
    Team,
    ValidationGate,
    WorkItem,
    WorkVersion,
    now,
)
from apc.schemas import (
    ArtifactCreate,
    ArtifactReferenceCreate,
    Claim,
    DashboardTemplateCreate,
    DashboardTemplateRevisionCreate,
    GateCreate,
    GateResult,
    OverviewUpdate,
    PMSummaryCreate,
    ProgressUpdate,
    ProjectCreate,
    TeamCreate,
    VersionCreate,
    WorkItemCreate,
)

app = FastAPI(title="Agent Project Control", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def event(
    db: Session,
    project_id: str,
    actor: str,
    event_type: str,
    message: str,
    work_item_id: str | None = None,
    version_id: str | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            project_id=project_id,
            work_item_id=work_item_id,
            version_id=version_id,
            actor=actor,
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
    )


def dump(obj):
    """Expose columns only; ORM internals and relationships never become API output."""
    if isinstance(obj, list):
        return [dump(item) for item in obj]
    return {column.key: getattr(obj, column.key) for column in inspect(obj).mapper.column_attrs}


def require_project(db: Session, project_id: str) -> Project:
    obj = db.get(Project, project_id)
    if not obj:
        raise HTTPException(404, "project not found")
    return obj


def require_item(db: Session, item_id: str) -> WorkItem:
    obj = db.get(WorkItem, item_id)
    if not obj:
        raise HTTPException(404, "work item not found")
    return obj


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/teams", status_code=status.HTTP_201_CREATED, response_model=None)
def create_team(body: TeamCreate, db: Session = Depends(db_session)) -> Team:
    team = Team(slug=body.slug, name=body.name)
    db.add(team)
    db.flush()
    db.commit()
    return dump(team)


@app.post("/projects", status_code=status.HTTP_201_CREATED, response_model=None)
def create_project(body: ProjectCreate, db: Session = Depends(db_session)) -> Project:
    if not db.get(Team, body.team_id):
        raise HTTPException(404, "team not found")
    project = Project(team_id=body.team_id, key=body.key, name=body.name)
    db.add(project)
    db.flush()
    event(db, project.id, body.actor, "PROJECT_CREATED", f"Created project {project.key}")
    db.commit()
    return dump(project)


@app.post("/projects/{project_id}/items", status_code=status.HTTP_201_CREATED, response_model=None)
def create_work_item(project_id: str, body: WorkItemCreate, db: Session = Depends(db_session)) -> WorkItem:
    require_project(db, project_id)
    if body.parent_id:
        parent = require_item(db, body.parent_id)
        if parent.project_id != project_id:
            raise HTTPException(422, "parent belongs to another project")
    item = WorkItem(project_id=project_id, **body.model_dump(exclude={"actor"}))
    db.add(item)
    db.flush()
    event(db, project_id, body.actor, "WORK_ITEM_CREATED", body.title, work_item_id=item.id)
    db.commit()
    return dump(item)


@app.post("/items/{item_id}/claim", response_model=None)
def claim_item(item_id: str, body: Claim, db: Session = Depends(db_session)) -> WorkItem:
    item = require_item(db, item_id)
    if item.status not in {"DRAFT", "QUEUED", "CLAIMED"} and item.owner_actor != body.actor:
        raise HTTPException(409, f"cannot claim item in {item.status}")
    item.owner_actor, item.status = body.actor, "CLAIMED"
    event(db, item.project_id, body.actor, "WORK_CLAIMED", "Claimed work item", item.id)
    db.commit()
    return dump(item)


@app.post("/items/{item_id}/progress", response_model=None)
def update_progress(item_id: str, body: ProgressUpdate, db: Session = Depends(db_session)) -> WorkItem:
    item = require_item(db, item_id)
    if item.owner_actor and item.owner_actor != body.actor:
        raise HTTPException(403, "only the current owner may report progress")
    if body.status:
        if body.status == "VERIFIED":
            raise HTTPException(422, "VERIFIED is granted only through gate completion")
        item.status = body.status
    event(db, item.project_id, body.actor, "PROGRESS_REPORTED", body.message, item.id, payload=body.payload)
    db.commit()
    return dump(item)


@app.post("/items/{item_id}/versions", status_code=status.HTTP_201_CREATED, response_model=None)
def create_version(item_id: str, body: VersionCreate, db: Session = Depends(db_session)) -> WorkVersion:
    item = require_item(db, item_id)
    ordinal = (db.scalar(select(WorkVersion.ordinal).where(WorkVersion.work_item_id == item_id).order_by(WorkVersion.ordinal.desc())) or 0) + 1
    version = WorkVersion(work_item_id=item_id, ordinal=ordinal, created_by=body.actor, **body.model_dump(exclude={"actor"}))
    db.add(version)
    db.flush()
    item.current_version_id, item.status = version.id, "WORKING"
    event(db, item.project_id, body.actor, "VERSION_CREATED", f"Created v{ordinal}", item.id, version.id)
    db.commit()
    return dump(version)


@app.post("/versions/{version_id}/gates", status_code=status.HTTP_201_CREATED, response_model=None)
def create_gate(version_id: str, body: GateCreate, db: Session = Depends(db_session)) -> ValidationGate:
    version = db.get(WorkVersion, version_id)
    if not version:
        raise HTTPException(404, "version not found")
    item = require_item(db, version.work_item_id)
    gate = ValidationGate(work_version_id=version_id, name=body.name, required=body.required)
    db.add(gate)
    db.flush()
    event(db, item.project_id, body.actor, "GATE_DECLARED", body.name, item.id, version.id)
    db.commit()
    return dump(gate)


@app.post("/gates/{gate_id}/result", response_model=None)
def record_gate_result(gate_id: str, body: GateResult, db: Session = Depends(db_session)) -> ValidationGate:
    gate = db.get(ValidationGate, gate_id)
    if not gate:
        raise HTTPException(404, "gate not found")
    if body.status in {"PASSED", "WAIVED"} and not body.evidence_uri:
        raise HTTPException(422, "PASSED/WAIVED requires an evidence_uri")
    version = db.get(WorkVersion, gate.work_version_id)
    item = require_item(db, version.work_item_id)
    gate.status, gate.evidence_uri, gate.evidence_sha256 = body.status, body.evidence_uri, body.evidence_sha256
    gate.checked_by, gate.checked_at = body.actor, now()
    event(db, item.project_id, body.actor, "GATE_RESULT", body.message, item.id, version.id, {"gate": gate.name, "status": body.status})
    required = db.scalars(select(ValidationGate).where(ValidationGate.work_version_id == version.id, ValidationGate.required.is_(True))).all()
    if required and all(x.status in {"PASSED", "WAIVED"} for x in required):
        version.state, item.status = "VERIFIED", "VERIFIED"
        event(db, item.project_id, "system", "VERSION_VERIFIED", f"v{version.ordinal} required gates closed", item.id, version.id)
    elif body.status == "FAILED":
        version.state, item.status = "FAILED", "BLOCKED"
    db.commit()
    return dump(gate)


@app.post("/projects/{project_id}/overview", response_model=None)
def update_overview(project_id: str, body: OverviewUpdate, db: Session = Depends(db_session)) -> ProjectOverviewRevision:
    require_project(db, project_id)
    revision = ProjectOverviewRevision(project_id=project_id, body_markdown=body.body_markdown, updated_by=body.actor)
    db.add(revision)
    event(db, project_id, body.actor, "OVERVIEW_REVISED", "Updated project overview")
    db.commit()
    return dump(revision)


@app.post("/projects/{project_id}/pm-summaries", status_code=status.HTTP_201_CREATED, response_model=None)
def create_pm_summary(project_id: str, body: PMSummaryCreate, db: Session = Depends(db_session)) -> PMSummaryEntry:
    require_project(db, project_id)
    summary = PMSummaryEntry(project_id=project_id, author=body.actor, body_markdown=body.body_markdown, evidence_refs=body.evidence_refs)
    db.add(summary)
    event(db, project_id, body.actor, "PM_SUMMARY_APPENDED", "Appended PM summary")
    db.commit()
    return dump(summary)


@app.post("/projects/{project_id}/artifacts", status_code=status.HTTP_201_CREATED, response_model=None)
def register_artifact(project_id: str, body: ArtifactCreate, db: Session = Depends(db_session)) -> Artifact:
    require_project(db, project_id)
    path = body.path.rstrip("/")
    is_db = path.endswith((".sqlite", ".sqlite3", ".db"))
    if is_db and ("/reports/" in path or "/frozen_" in path):
        raise HTTPException(422, "database copies cannot be registered under reports or frozen packages")
    artifact = Artifact(project_id=project_id, path=path, owner_actor=body.actor, **body.model_dump(exclude={"actor", "path"}))
    db.add(artifact)
    db.flush()
    event(db, project_id, body.actor, "ARTIFACT_REGISTERED", path, payload={"sha256": body.sha256, "bytes": body.bytes})
    db.commit()
    return dump(artifact)


@app.post("/artifacts/{artifact_id}/references", status_code=status.HTTP_201_CREATED, response_model=None)
def reference_artifact(artifact_id: str, body: ArtifactReferenceCreate, db: Session = Depends(db_session)) -> ArtifactReference:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(404, "artifact not found")
    ref = ArtifactReference(artifact_id=artifact_id, ref_kind=body.ref_kind, ref_id=body.ref_id)
    db.add(ref)
    event(db, artifact.project_id, body.actor, "ARTIFACT_REFERENCED", artifact.path, payload={"ref_kind": body.ref_kind, "ref_id": body.ref_id})
    db.commit()
    return dump(ref)


@app.get("/artifacts/{artifact_id}/deletion-check")
def artifact_deletion_check(artifact_id: str, db: Session = Depends(db_session)) -> dict:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(404, "artifact not found")
    refs = db.scalars(select(ArtifactReference).where(ArtifactReference.artifact_id == artifact_id)).all()
    protected = artifact.retention_state in {"UNIQUE_INPUT", "ROLLBACK_POINT"}
    return {
        "artifact_id": artifact_id,
        "path": artifact.path,
        "retention_state": artifact.retention_state,
        "references": [{"kind": r.ref_kind, "id": r.ref_id} for r in refs],
        "allowed": not protected and not refs,
        "reason": "protected retention state" if protected else ("still referenced" if refs else "no live references"),
    }


@app.get("/projects/{project_id}/history", response_model=None)
def project_history(project_id: str, db: Session = Depends(db_session)) -> list[AuditEvent]:
    require_project(db, project_id)
    return dump(db.scalars(select(AuditEvent).where(AuditEvent.project_id == project_id).order_by(AuditEvent.created_at)).all())


@app.post("/dashboard-templates", status_code=status.HTTP_201_CREATED, response_model=None)
def create_dashboard_template(body: DashboardTemplateCreate, db: Session = Depends(db_session)) -> DashboardTemplate:
    if body.team_id and not db.get(Team, body.team_id):
        raise HTTPException(404, "team not found")
    if body.project_id:
        require_project(db, body.project_id)
    template = DashboardTemplate(
        team_id=body.team_id,
        project_id=body.project_id,
        name=body.name,
        description=body.description,
        created_by=body.actor,
    )
    db.add(template)
    db.flush()
    revision = DashboardTemplateRevision(template_id=template.id, ordinal=1, layout=body.layout, created_by=body.actor)
    db.add(revision)
    db.flush()
    template.current_revision_id = revision.id
    db.commit()
    return dump(template)


@app.post("/dashboard-templates/{template_id}/revisions", status_code=status.HTTP_201_CREATED, response_model=None)
def revise_dashboard_template(template_id: str, body: DashboardTemplateRevisionCreate, db: Session = Depends(db_session)) -> DashboardTemplateRevision:
    template = db.get(DashboardTemplate, template_id)
    if not template:
        raise HTTPException(404, "dashboard template not found")
    ordinal = (db.scalar(select(DashboardTemplateRevision.ordinal).where(DashboardTemplateRevision.template_id == template_id).order_by(DashboardTemplateRevision.ordinal.desc())) or 0) + 1
    revision = DashboardTemplateRevision(template_id=template_id, ordinal=ordinal, layout=body.layout, created_by=body.actor)
    db.add(revision)
    db.flush()
    template.current_revision_id = revision.id
    db.commit()
    return dump(revision)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: Session = Depends(db_session)) -> str:
    projects = db.scalars(select(Project).order_by(Project.key)).all()
    rows = []
    for project in projects:
        items = db.scalars(select(WorkItem).where(WorkItem.project_id == project.id)).all()
        blocked = sum(1 for item in items if item.status in {"BLOCKED", "HOLD", "FAILED"})
        verified = sum(1 for item in items if item.status == "VERIFIED")
        rows.append(f"<tr><td>{project.key}</td><td>{project.name}</td><td>{len(items)}</td><td>{verified}</td><td>{blocked}</td><td><a href='/projects/{project.id}/history'>history</a></td></tr>")
    body = "".join(rows) or "<tr><td colspan='6'>No projects yet</td></tr>"
    return f'''<!doctype html><html><head><title>COAGENTS Dashboard</title>
<style>body{{font-family:system-ui;margin:2rem;background:#10151f;color:#e8edf5}} table{{border-collapse:collapse;width:100%;background:#192231}}td,th{{padding:.7rem;border-bottom:1px solid #344155;text-align:left}}th{{color:#90caf9}}a{{color:#80cbc4}}.note{{color:#aab8c8}}</style>
</head><body><h1>COAGENTS</h1><p class='note'>Project control dashboard — current state links to immutable history.</p>
<table><thead><tr><th>Key</th><th>Project</th><th>Items</th><th>Verified</th><th>Blocked/Hold</th><th>Timeline</th></tr></thead><tbody>{body}</tbody></table>
<p class='note'>Templates are API-managed and revisioned at <code>/dashboard-templates</code>. This initial view intentionally remains read-only.</p>
</body></html>'''


@app.get("/items/{item_id}/history")
def item_history(item_id: str, db: Session = Depends(db_session)) -> dict:
    item = require_item(db, item_id)
    versions = db.scalars(select(WorkVersion).where(WorkVersion.work_item_id == item_id).order_by(WorkVersion.ordinal)).all()
    events = db.scalars(select(AuditEvent).where(AuditEvent.work_item_id == item_id).order_by(AuditEvent.created_at)).all()
    gates = {v.id: db.scalars(select(ValidationGate).where(ValidationGate.work_version_id == v.id)).all() for v in versions}
    return {"item": dump(item), "versions": dump(versions), "gates": {key: dump(value) for key, value in gates.items()}, "events": dump(events)}
