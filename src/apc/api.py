"""COAGENTS: one service for the dashboard, agents, and project records."""

import hashlib
import secrets
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, event as sql_event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apc import models as m
from apc import schemas as s
from apc.settings import Settings

STATIC = Path(__file__).parent / "static"


def dump(obj):
    if isinstance(obj, (list, tuple)):
        return [dump(row) for row in obj]
    if obj is None:
        return None
    return {col.key: getattr(obj, col.key) for col in inspect(obj).mapper.column_attrs}


def get(db, cls, key):
    row = db.get(cls, key)
    if row is None:
        raise HTTPException(404, f"{cls.__name__} not found")
    return row


def emit(db, project_id, actor, kind, message, item=None, version=None, payload=None):
    db.add(m.AuditEvent(
        project_id=project_id, actor=actor, event_type=kind, message=message,
        work_item_id=item, version_id=version, payload=payload or {},
    ))


def command_actor(db, actor, roles=None):
    principal = db.info.get("principal")
    if principal and principal["actor"] != actor:
        raise HTTPException(403, "actor does not match the authenticated identity")
    if actor == "pm":
        return {"actor": "pm", "role": "PM", "team_id": None}
    row = db.scalar(select(m.Member).where(m.Member.actor == actor))
    if not row:
        raise HTTPException(422, "register this member before issuing commands")
    if roles and row.role not in roles:
        raise HTTPException(403, "this action requires " + "/".join(roles))
    return dump(row)


def project_access(db, project_id, actor=None):
    project = get(db, m.Project, project_id)
    principal = command_actor(db, actor) if actor else db.info.get("principal")
    if principal and principal["role"] != "PM":
        teams = set(db.scalars(select(m.ProjectTeam.team_id).where(
            m.ProjectTeam.project_id == project_id
        )).all()) | {project.team_id}
        if principal.get("team_id") not in teams:
            raise HTTPException(403, "project is outside the member's teams")
    return project


def locked_item(db, item_id, actor=None):
    row = db.scalar(select(m.WorkItem).where(m.WorkItem.id == item_id).with_for_update())
    if not row:
        raise HTTPException(404, "work item not found")
    project_access(db, row.project_id, actor)
    return row


def details(db, item):
    row = db.get(m.WorkDetails, item.id)
    if not row:
        row = m.WorkDetails(work_item_id=item.id)
        db.add(row)
        db.flush()
    return row


def item_view(db, item):
    result = dump(item)
    detail = db.get(m.WorkDetails, item.id)
    result.update(
        description=detail.description if detail else "",
        team_id=detail.team_id if detail else None,
        priority=detail.priority if detail else "NORMAL",
        progress_percent=detail.progress_percent if detail else 0,
        labels=detail.labels if detail else [],
    )
    version = db.get(m.WorkVersion, item.current_version_id) if item.current_version_id else None
    result["current_version"] = dump(version)
    gates = db.scalars(select(m.ValidationGate).where(
        m.ValidationGate.work_version_id == version.id
    )).all() if version else []
    result["gates"] = dump(gates)
    required = [gate for gate in gates if gate.required]
    result["validation"] = (
        "FAILED" if any(gate.status == "FAILED" for gate in required) else
        "PASSED" if required and all(gate.status in {"PASSED", "WAIVED"} for gate in required) else
        "PENDING" if required else "NOT_DECLARED"
    )
    result["dependencies"] = list(db.scalars(select(m.WorkDependency.depends_on_id).where(
        m.WorkDependency.item_id == item.id
    )).all())
    return result


def deletion_check(db, artifact):
    refs = db.scalars(select(m.ArtifactReference).where(
        m.ArtifactReference.artifact_id == artifact.id
    )).all()
    protected = artifact.retention_state in {"UNIQUE_INPUT", "ROLLBACK_POINT", "DELETED"}
    return {
        "artifact_id": artifact.id, "path": artifact.path,
        "retention_state": artifact.retention_state, "references": dump(refs),
        "allowed": not protected and not refs,
        "reason": "protected or already deleted" if protected else "still referenced" if refs else "unreferenced",
        "scope": "registry only; inspect actual file/process use before physical deletion",
    }


def locked_artifact(db, artifact_id, actor):
    row = db.scalar(select(m.Artifact).where(m.Artifact.id == artifact_id).with_for_update())
    if not row:
        raise HTTPException(404, "artifact not found")
    project_access(db, row.project_id, actor)
    return row


DEFAULT_LAYOUT = {
    "title": "專案管制總覽", "statuses": [],
    "widgets": [
        {"type": "metric", "title": "工作項目", "query": "items"},
        {"type": "metric", "title": "已驗證", "query": "verified"},
        {"type": "metric", "title": "阻塞 / HOLD", "query": "blocked"},
        {"type": "metric", "title": "待驗證格", "query": "pending_gates"},
        {"type": "table", "title": "工作與交付版本", "query": "items",
         "columns": ["key", "title", "team", "owner_actor", "status", "version", "validation", "progress"]},
        {"type": "summary", "title": "PM 整合紀錄", "query": "summaries"},
        {"type": "artifacts", "title": "檔案與資料資產", "query": "artifacts"},
        {"type": "timeline", "title": "最新歷程", "query": "events"},
    ],
}


def create_app(database_url=None, admin_token=None):
    settings = Settings()
    url = database_url or settings.database_url
    token = settings.coagents_admin_token if admin_token is None else admin_token
    opts = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if url in {"sqlite://", "sqlite:///:memory:"}:
        opts["poolclass"] = StaticPool
    engine = create_engine(url, **opts)
    if url.startswith("sqlite"):
        @sql_event.listens_for(engine, "connect")
        def sqlite_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_app):
        m.Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title="COAGENTS", version="0.2.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessions = sessions

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        public = request.url.path in {"/", "/dashboard", "/healthz", "/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"} or request.url.path.startswith("/static/")
        request.state.principal = None
        if token and not public:
            bearer = request.headers.get("authorization", "")
            value = bearer[7:] if bearer.startswith("Bearer ") else ""
            if secrets.compare_digest(value, token):
                request.state.principal = {"actor": "pm", "role": "PM", "team_id": None}
            else:
                with sessions() as db:
                    key = db.scalar(select(m.MemberKey).where(
                        m.MemberKey.token_hash == hashlib.sha256(value.encode()).hexdigest()
                    )) if value else None
                    member = db.get(m.Member, key.member_id) if key else None
                    if not member:
                        return JSONResponse({"detail": "a valid COAGENTS token is required"}, status_code=401)
                    request.state.principal = dump(member)
        return await call_next(request)

    def db_session(request: Request):
        with sessions() as db:
            db.info["principal"] = request.state.principal
            yield db

    DB = Depends(db_session)

    @app.exception_handler(IntegrityError)
    async def conflict(_request, _exc):
        return JSONResponse({"detail": "duplicate key or invalid reference"}, status_code=409)

    @app.get("/healthz")
    def health():
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return {"status": "ok", "service": "COAGENTS", "version": "0.2.0"}

    @app.get("/session")
    def identity(request: Request):
        return {"auth_enabled": bool(token), "principal": request.state.principal}

    @app.get("/teams")
    def list_teams(db: Session = DB):
        principal = db.info.get("principal")
        rows = db.scalars(select(m.Team).order_by(m.Team.name)).all()
        if principal and principal["role"] != "PM":
            rows = [row for row in rows if row.id == principal["team_id"]]
        return dump(rows)

    @app.post("/teams", status_code=201)
    def create_team(body: s.TeamCreate, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        row = m.Team(slug=body.slug, name=body.name)
        db.add(row)
        db.commit()
        return dump(row)

    @app.get("/members")
    def list_members(db: Session = DB):
        rows = db.scalars(select(m.Member).order_by(m.Member.name)).all()
        principal = db.info.get("principal")
        if principal and principal["role"] != "PM":
            rows = [row for row in rows if row.team_id == principal["team_id"]]
        return dump(rows)

    @app.post("/members", status_code=201)
    def create_member(body: s.MemberCreate, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        if body.member_actor == "pm":
            raise HTTPException(422, "pm is reserved for the administrator")
        if body.team_id:
            get(db, m.Team, body.team_id)
        row = m.Member(actor=body.member_actor, name=body.name, kind=body.kind,
                       role=body.role, team_id=body.team_id)
        db.add(row)
        db.commit()
        return dump(row)

    @app.post("/members/{member_id}/keys", status_code=201)
    def issue_member_key(member_id: str, body: s.Claim, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        get(db, m.Member, member_id)
        value = "coa_" + secrets.token_urlsafe(32)
        row = m.MemberKey(member_id=member_id, token_hash=hashlib.sha256(value.encode()).hexdigest())
        db.add(row)
        db.commit()
        return {"id": row.id, "token": value, "notice": "save now; only the hash is stored"}

    @app.delete("/members/{member_id}/keys/{key_id}")
    def revoke_member_key(member_id: str, key_id: str, body: s.Claim, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        row = get(db, m.MemberKey, key_id)
        if row.member_id != member_id:
            raise HTTPException(404, "key not found for this member")
        db.delete(row)
        db.commit()
        return {"revoked": True}

    @app.get("/projects")
    def list_projects(db: Session = DB):
        rows = db.scalars(select(m.Project).order_by(m.Project.key)).all()
        principal = db.info.get("principal")
        if principal and principal["role"] != "PM":
            linked = set(db.scalars(select(m.ProjectTeam.project_id).where(
                m.ProjectTeam.team_id == principal["team_id"]
            )).all())
            rows = [row for row in rows if row.team_id == principal["team_id"] or row.id in linked]
        return [dict(dump(row), team_ids=list(db.scalars(select(m.ProjectTeam.team_id).where(
            m.ProjectTeam.project_id == row.id
        )).all())) for row in rows]

    @app.post("/projects", status_code=201)
    def create_project(body: s.ProjectCreate, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        for team_id in set(body.team_ids) | {body.team_id}:
            get(db, m.Team, team_id)
        row = m.Project(team_id=body.team_id, key=body.key, name=body.name)
        db.add(row)
        db.flush()
        for team_id in set(body.team_ids) | {body.team_id}:
            db.add(m.ProjectTeam(project_id=row.id, team_id=team_id))
        emit(db, row.id, body.actor, "PROJECT_CREATED", body.name)
        db.commit()
        return dump(row)

    @app.post("/projects/{project_id}/items", status_code=201)
    def create_item(project_id: str, body: s.WorkItemCreate, db: Session = DB):
        project = project_access(db, project_id, body.actor)
        principal = command_actor(db, body.actor)
        if body.parent_id and get(db, m.WorkItem, body.parent_id).project_id != project_id:
            raise HTTPException(422, "parent must belong to this project")
        team_id = body.team_id or project.team_id
        linked = db.scalar(select(m.ProjectTeam.id).where(
            m.ProjectTeam.project_id == project_id, m.ProjectTeam.team_id == team_id
        ))
        if team_id != project.team_id and not linked:
            raise HTTPException(422, "item team must participate in this project")
        if principal["role"] != "PM" and team_id != principal["team_id"]:
            raise HTTPException(403, "create work for your own team")
        row = m.WorkItem(project_id=project_id, key=body.key, kind=body.kind,
                         title=body.title, parent_id=body.parent_id)
        db.add(row)
        db.flush()
        db.add(m.WorkDetails(work_item_id=row.id, team_id=team_id, description=body.description,
                             priority=body.priority, labels=body.labels))
        emit(db, project_id, body.actor, "WORK_ITEM_CREATED", body.title, row.id)
        db.commit()
        return item_view(db, row)

    @app.get("/items/{item_id}")
    def read_item(item_id: str, db: Session = DB):
        return item_view(db, locked_item(db, item_id))

    @app.patch("/items/{item_id}")
    def edit_item(item_id: str, body: s.WorkItemUpdate, db: Session = DB):
        row = locked_item(db, item_id, body.actor)
        author = command_actor(db, body.actor)
        if row.owner_actor and row.owner_actor != body.actor and author["role"] != "PM":
            raise HTTPException(403, "only owner or PM may edit this item")
        before = item_view(db, row)
        detail = details(db, row)
        for key, value in body.model_dump(exclude={"actor"}, exclude_none=True).items():
            setattr(row if key == "title" else detail, key, value)
        emit(db, row.project_id, body.actor, "WORK_ITEM_UPDATED", row.title, row.id,
             payload={"before": {key: before[key] for key in body.model_fields_set if key != "actor"},
                      "after": body.model_dump(exclude={"actor"}, exclude_none=True)})
        db.commit()
        return item_view(db, row)

    @app.post("/items/{item_id}/claim")
    def claim(item_id: str, body: s.Claim, db: Session = DB):
        row = locked_item(db, item_id, body.actor)
        actor = command_actor(db, body.actor)
        detail = details(db, row)
        if actor["role"] != "PM" and detail.team_id not in {None, actor["team_id"]}:
            raise HTTPException(403, "this item belongs to another team")
        if row.owner_actor and row.owner_actor != body.actor:
            raise HTTPException(409, "work is already claimed by " + row.owner_actor)
        if row.status in {"VERIFIED", "CLOSED"}:
            raise HTTPException(409, "create a new delivery version to reopen this item")
        row.owner_actor, row.status = body.actor, "CLAIMED"
        emit(db, row.project_id, body.actor, "WORK_CLAIMED", "認領工作", row.id)
        db.commit()
        return item_view(db, row)

    @app.post("/items/{item_id}/progress")
    def progress(item_id: str, body: s.ProgressUpdate, db: Session = DB):
        row = locked_item(db, item_id, body.actor)
        if row.owner_actor != body.actor:
            raise HTTPException(403, "claim this item before reporting progress")
        if row.status in {"VERIFIED", "CLOSED"}:
            raise HTTPException(409, "create a new delivery version before changing completed work")
        if body.status:
            row.status = body.status
        if body.progress_percent is not None:
            details(db, row).progress_percent = body.progress_percent
        emit(db, row.project_id, body.actor, "PROGRESS_REPORTED", body.message, row.id,
             row.current_version_id, dict(body.payload, status=row.status,
                                          progress_percent=body.progress_percent))
        db.commit()
        return item_view(db, row)

    @app.post("/items/{item_id}/dependencies", status_code=201)
    def dependency(item_id: str, body: s.DependencyCreate, db: Session = DB):
        # Serialize graph edits per project: disjoint edges can jointly form a cycle.
        item = get(db, m.WorkItem, item_id)
        project_access(db, item.project_id, body.actor)
        db.scalar(select(m.Project).where(m.Project.id == item.project_id).with_for_update())
        row = locked_item(db, item_id, body.actor)
        other = locked_item(db, body.depends_on_id, body.actor)
        if other.project_id != row.project_id:
            raise HTTPException(422, "dependencies must belong to the same shared project")
        edges = db.scalars(select(m.WorkDependency)).all()
        graph = {}
        for edge in edges:
            graph.setdefault(edge.item_id, []).append(edge.depends_on_id)
        pending, seen = [other.id], set()
        while pending:
            key = pending.pop()
            if key == row.id:
                raise HTTPException(409, "dependency would create a cycle")
            if key not in seen:
                seen.add(key)
                pending.extend(graph.get(key, []))
        edge = m.WorkDependency(item_id=row.id, depends_on_id=other.id)
        db.add(edge)
        emit(db, row.project_id, body.actor, "DEPENDENCY_ADDED", other.key, row.id,
             payload={"depends_on_id": other.id})
        db.commit()
        return dump(edge)

    @app.post("/items/{item_id}/versions", status_code=201)
    def version(item_id: str, body: s.VersionCreate, db: Session = DB):
        row = locked_item(db, item_id, body.actor)
        author = command_actor(db, body.actor)
        if row.owner_actor != body.actor and author["role"] != "PM":
            raise HTTPException(403, "claim this item before creating a version")
        ordinal = (db.scalar(select(m.WorkVersion.ordinal).where(
            m.WorkVersion.work_item_id == item_id
        ).order_by(m.WorkVersion.ordinal.desc()).limit(1)) or 0) + 1
        result = m.WorkVersion(work_item_id=row.id, ordinal=ordinal, created_by=body.actor,
                               **body.model_dump(exclude={"actor"}))
        db.add(result)
        db.flush()
        row.current_version_id, row.status = result.id, "WORKING"
        details(db, row).progress_percent = 0
        emit(db, row.project_id, body.actor, "VERSION_CREATED", body.change_note, row.id,
             result.id, {"ordinal": ordinal, "source_ref": body.source_ref})
        db.commit()
        return dump(result)

    @app.post("/versions/{version_id}/gates", status_code=201)
    def gate(version_id: str, body: s.GateCreate, db: Session = DB):
        version = get(db, m.WorkVersion, version_id)
        row = locked_item(db, version.work_item_id, body.actor)
        db.refresh(version)  # A concurrent reviewer may have finalized it while we waited.
        command_actor(db, body.actor, {"PM", "REVIEWER"})
        if version.state in {"VERIFIED", "FAILED"}:
            raise HTTPException(409, "declare gates on a new version")
        result = m.ValidationGate(work_version_id=version.id, name=body.name, required=body.required)
        db.add(result)
        emit(db, row.project_id, body.actor, "GATE_DECLARED", body.name, row.id, version.id)
        db.commit()
        return dump(result)

    @app.post("/gates/{gate_id}/result")
    def gate_result(gate_id: str, body: s.GateResult, db: Session = DB):
        gate = get(db, m.ValidationGate, gate_id)
        version = get(db, m.WorkVersion, gate.work_version_id)
        row = locked_item(db, version.work_item_id, body.actor)
        db.refresh(gate)
        db.refresh(version)
        command_actor(db, body.actor, {"PM"} if body.status == "WAIVED" else {"PM", "REVIEWER"})
        if body.actor == version.created_by:
            raise HTTPException(403, "a delivery must be validated by another member")
        if gate.status != "PENDING":
            raise HTTPException(409, "gate results are final; create a successor version for corrections")
        gate.status, gate.evidence_uri, gate.evidence_sha256 = body.status, body.evidence_uri, body.evidence_sha256
        gate.checked_by, gate.checked_at = body.actor, m.now()
        db.flush()
        required = db.scalars(select(m.ValidationGate).where(
            m.ValidationGate.work_version_id == version.id, m.ValidationGate.required.is_(True)
        )).all()
        failed = any(value.status == "FAILED" for value in required)
        passed = bool(required) and all(value.status in {"PASSED", "WAIVED"} for value in required)
        version.state = "FAILED" if failed else "VERIFIED" if passed else "VALIDATING"
        if row.current_version_id == version.id:
            row.status = "BLOCKED" if failed else "VERIFIED" if passed else "VALIDATING"
        emit(db, row.project_id, body.actor, "GATE_RESULT", body.message, row.id, version.id,
             {"gate": gate.name, "status": body.status, "evidence_uri": body.evidence_uri,
              "evidence_sha256": body.evidence_sha256, "version_state": version.state})
        db.commit()
        return dump(gate)

    @app.post("/items/{item_id}/close")
    def close(item_id: str, body: s.Claim, db: Session = DB):
        row = locked_item(db, item_id, body.actor)
        command_actor(db, body.actor, {"PM"})
        if row.status != "VERIFIED":
            raise HTTPException(409, "current delivery must be verified before closure")
        for dep in db.scalars(select(m.WorkDependency).where(m.WorkDependency.item_id == item_id)):
            if get(db, m.WorkItem, dep.depends_on_id).status not in {"VERIFIED", "CLOSED"}:
                raise HTTPException(409, "a dependency is not verified")
        row.status = "CLOSED"
        emit(db, row.project_id, body.actor, "WORK_CLOSED", "結案", row.id, row.current_version_id)
        db.commit()
        return item_view(db, row)

    @app.post("/projects/{project_id}/overview", status_code=201)
    def overview(project_id: str, body: s.OverviewUpdate, db: Session = DB):
        project_access(db, project_id, body.actor)
        command_actor(db, body.actor, {"PM"})
        row = m.ProjectOverviewRevision(project_id=project_id, body_markdown=body.body_markdown,
                                         updated_by=body.actor)
        db.add(row)
        emit(db, project_id, body.actor, "OVERVIEW_REVISED", body.body_markdown)
        db.commit()
        return dump(row)

    @app.post("/projects/{project_id}/pm-summaries", status_code=201)
    def summary(project_id: str, body: s.PMSummaryCreate, db: Session = DB):
        project_access(db, project_id, body.actor)
        command_actor(db, body.actor, {"PM"})
        row = m.PMSummaryEntry(project_id=project_id, author=body.actor,
                              body_markdown=body.body_markdown, evidence_refs=body.evidence_refs)
        db.add(row)
        emit(db, project_id, body.actor, "PM_SUMMARY_APPENDED", body.body_markdown,
             payload={"evidence_refs": body.evidence_refs})
        db.commit()
        return dump(row)

    @app.get("/projects/{project_id}/history")
    def history(project_id: str, db: Session = DB):
        project_access(db, project_id)
        return dump(db.scalars(select(m.AuditEvent).where(
            m.AuditEvent.project_id == project_id
        ).order_by(m.AuditEvent.created_at, m.AuditEvent.id)).all())

    @app.get("/items/{item_id}/history")
    def item_history(item_id: str, db: Session = DB):
        row = locked_item(db, item_id)
        versions = db.scalars(select(m.WorkVersion).where(
            m.WorkVersion.work_item_id == item_id
        ).order_by(m.WorkVersion.ordinal)).all()
        return {
            "item": item_view(db, row), "versions": dump(versions),
            "gates": {value.id: dump(db.scalars(select(m.ValidationGate).where(
                m.ValidationGate.work_version_id == value.id)).all()) for value in versions},
            "events": dump(db.scalars(select(m.AuditEvent).where(
                m.AuditEvent.work_item_id == item_id
            ).order_by(m.AuditEvent.created_at, m.AuditEvent.id)).all()),
        }

    @app.post("/projects/{project_id}/artifacts", status_code=201)
    def artifact(project_id: str, body: s.ArtifactCreate, db: Session = DB):
        project_access(db, project_id, body.actor)
        path = str(PurePosixPath(body.path.replace("\\", "/")))
        if not path.startswith("/") or ".." in PurePosixPath(path).parts:
            raise HTTPException(422, "use a normalized absolute path")
        db_file = path.lower().endswith((".sqlite", ".sqlite3", ".db")) or "sqlite" in body.media_type
        components = PurePosixPath(path).parts
        if db_file and any(value == "reports" or value.lower().startswith("frozen") for value in components):
            raise HTTPException(422, "database copies must be registered outside reports/frozen packages")
        row = m.Artifact(project_id=project_id, owner_actor=body.actor,
                         retention_state=body.purpose, path=path,
                         **body.model_dump(exclude={"actor", "path"}))
        db.add(row)
        emit(db, project_id, body.actor, "ARTIFACT_REGISTERED", path,
             payload={"sha256": body.sha256, "bytes": body.bytes, "purpose": body.purpose})
        db.commit()
        return dump(row)

    @app.post("/artifacts/{artifact_id}/references", status_code=201)
    def artifact_ref(artifact_id: str, body: s.ArtifactReferenceCreate, db: Session = DB):
        row = locked_artifact(db, artifact_id, body.actor)
        if row.retention_state == "DELETED":
            raise HTTPException(409, "a deleted artifact cannot receive new references")
        cls = {"VERSION": m.WorkVersion, "GATE": m.ValidationGate, "SUMMARY": m.PMSummaryEntry}[body.ref_kind]
        target = get(db, cls, body.ref_id)
        if body.ref_kind == "GATE":
            target = get(db, m.WorkVersion, target.work_version_id)
        target_project = target.project_id if body.ref_kind == "SUMMARY" else get(
            db, m.WorkItem, target.work_item_id
        ).project_id
        if target_project != row.project_id:
            raise HTTPException(422, "artifact and reference must share a project")
        ref = m.ArtifactReference(artifact_id=row.id, ref_kind=body.ref_kind, ref_id=body.ref_id)
        db.add(ref)
        emit(db, row.project_id, body.actor, "ARTIFACT_REFERENCED", row.path,
             payload={"ref_kind": body.ref_kind, "ref_id": body.ref_id})
        db.commit()
        return dump(ref)

    @app.get("/artifacts/{artifact_id}/deletion-check")
    def check_delete(artifact_id: str, db: Session = DB):
        row = get(db, m.Artifact, artifact_id)
        project_access(db, row.project_id)
        return deletion_check(db, row)

    @app.post("/artifacts/{artifact_id}/deleted")
    def mark_deleted(artifact_id: str, body: s.ArtifactDeleted, db: Session = DB):
        row = locked_artifact(db, artifact_id, body.actor)
        command_actor(db, body.actor, {"PM"})
        if not deletion_check(db, row)["allowed"]:
            raise HTTPException(409, "artifact is protected or referenced")
        row.retention_state = "DELETED"
        emit(db, row.project_id, body.actor, "ARTIFACT_DELETION_REPORTED", body.message,
             payload={"path": row.path, "sha256": row.sha256, "bytes": row.bytes})
        db.commit()
        return dump(row)

    @app.get("/dashboard-templates")
    def templates(db: Session = DB):
        principal = db.info.get("principal")
        rows = db.scalars(select(m.DashboardTemplate).order_by(m.DashboardTemplate.created_at)).all()
        output = []
        for row in rows:
            if principal and principal["role"] != "PM":
                if row.team_id and row.team_id != principal["team_id"]:
                    continue
                if row.project_id:
                    try:
                        project_access(db, row.project_id)
                    except HTTPException:
                        continue
            output.append(dict(dump(row), revisions=dump(db.scalars(select(
                m.DashboardTemplateRevision
            ).where(m.DashboardTemplateRevision.template_id == row.id).order_by(
                m.DashboardTemplateRevision.ordinal
            )).all())))
        return output

    @app.post("/dashboard-templates", status_code=201)
    def template_create(body: s.DashboardTemplateCreate, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        if body.team_id:
            get(db, m.Team, body.team_id)
        if body.project_id:
            project_access(db, body.project_id, body.actor)
        row = m.DashboardTemplate(**body.model_dump(exclude={"actor", "layout"}), created_by=body.actor)
        db.add(row)
        db.flush()
        rev = m.DashboardTemplateRevision(template_id=row.id, ordinal=1,
                                           layout=body.layout.model_dump(), created_by=body.actor)
        db.add(rev)
        db.flush()
        row.current_revision_id = rev.id
        db.commit()
        return dict(dump(row), revision=dump(rev))

    @app.post("/dashboard-templates/{template_id}/revisions", status_code=201)
    def template_revision(template_id: str, body: s.DashboardTemplateRevisionCreate, db: Session = DB):
        command_actor(db, body.actor, {"PM"})
        row = db.scalar(select(m.DashboardTemplate).where(
            m.DashboardTemplate.id == template_id
        ).with_for_update())
        if not row:
            raise HTTPException(404, "template not found")
        ordinal = (db.scalar(select(m.DashboardTemplateRevision.ordinal).where(
            m.DashboardTemplateRevision.template_id == template_id
        ).order_by(m.DashboardTemplateRevision.ordinal.desc()).limit(1)) or 0) + 1
        rev = m.DashboardTemplateRevision(template_id=row.id, ordinal=ordinal,
                                           layout=body.layout.model_dump(), created_by=body.actor)
        db.add(rev)
        db.flush()
        row.current_revision_id = rev.id
        db.commit()
        return dump(rev)

    @app.get("/workspace")
    def workspace(project_id: str | None = None, db: Session = DB):
        projects = list_projects(db)
        ids = [value["id"] for value in projects]
        if project_id:
            project_access(db, project_id)
            ids = [project_id]
        items = db.scalars(select(m.WorkItem).where(m.WorkItem.project_id.in_(ids)).order_by(
            m.WorkItem.created_at, m.WorkItem.key
        )).all()
        return {
            "projects": [value for value in projects if value["id"] in ids],
            "teams": list_teams(db), "members": list_members(db),
            "items": [item_view(db, row) for row in items],
            "events": dump(db.scalars(select(m.AuditEvent).where(
                m.AuditEvent.project_id.in_(ids)
            ).order_by(m.AuditEvent.created_at.desc()).limit(200)).all()),
            "summaries": dump(db.scalars(select(m.PMSummaryEntry).where(
                m.PMSummaryEntry.project_id.in_(ids)
            ).order_by(m.PMSummaryEntry.created_at.desc())).all()),
            "overviews": dump(db.scalars(select(m.ProjectOverviewRevision).where(
                m.ProjectOverviewRevision.project_id.in_(ids)
            ).order_by(m.ProjectOverviewRevision.created_at.desc())).all()),
            "artifacts": [dict(dump(row), deletion_check=deletion_check(db, row)) for row in db.scalars(
                select(m.Artifact).where(m.Artifact.project_id.in_(ids))
            ).all()],
            "default_layout": DEFAULT_LAYOUT,
        }

    @app.get("/dashboard")
    @app.get("/")
    def dashboard():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
