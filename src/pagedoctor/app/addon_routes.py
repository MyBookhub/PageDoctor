from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from pagedoctor.app.addon_auth import require_addon_token
from pagedoctor.app.container import get_container
from pagedoctor.app.routes import execute_in_background
from pagedoctor.domain.errors import DocumentAccessDeniedError, RunNotFoundError
from pagedoctor.domain.models.finding import Category, Finding, Priority
from pagedoctor.domain.models.run import RunStatus
from pagedoctor.domain.services.comment_format import findings_from_comments, parse_comment_body
from pagedoctor.domain.services.idempotency import finding_key
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

addon_router = APIRouter(prefix="/docs", dependencies=[Depends(require_addon_token)])


class AddonFinding(BaseModel):
    key: str
    quote: str
    proposed_change: str
    reason_de: str
    category: Category
    priority: Priority


class DocFindings(BaseModel):
    doc_id: str
    findings: list[AddonFinding]


class DocState(BaseModel):
    doc_id: str
    latest_run_id: UUID | None
    latest_status: RunStatus | None
    latest_finding_count: int


class ReviewStarted(BaseModel):
    run_id: UUID
    status: RunStatus


class RunStatusResponse(BaseModel):
    run_id: UUID
    status: RunStatus
    finding_count: int
    started_at: datetime | None
    finished_at: datetime | None


class ResolveResult(BaseModel):
    key: str
    resolved: bool


def to_addon_finding(doc_id: str, finding: Finding) -> AddonFinding:
    suggestion = finding.suggestion
    return AddonFinding(
        key=finding_key(doc_id, finding),
        quote=suggestion.original_text,
        proposed_change=suggestion.proposed_change,
        reason_de=suggestion.reason_de,
        category=finding.category,
        priority=finding.priority,
    )


@addon_router.get("/{doc_id}/findings")
def get_doc_findings(doc_id: str, request: Request) -> DocFindings:
    # Always re-derived live from the Drive comments Sophie already posted — the add-on
    # has no separate copy of finding content anywhere (§9). "Syncing" is just calling this
    # endpoint again; a resolved comment naturally drops out via findings_from_comments.
    container = get_container(request)
    source = container.build_comments_source()
    try:
        comments = source.read_comments(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    findings = findings_from_comments(comments)
    logger.info("served add-on findings", extra={"finding_count": len(findings)})
    return DocFindings(
        doc_id=doc_id, findings=[to_addon_finding(doc_id, finding) for finding in findings]
    )


@addon_router.get("/{doc_id}/state")
def get_doc_state(doc_id: str, request: Request) -> DocState:
    container = get_container(request)
    previous = container.repository.list_for_doc(doc_id, limit=1)
    latest = previous[0] if previous else None
    return DocState(
        doc_id=doc_id,
        latest_run_id=latest.id if latest else None,
        latest_status=latest.status if latest else None,
        latest_finding_count=latest.finding_count if latest else 0,
    )


@addon_router.post("/{doc_id}/review")
def start_doc_review(
    doc_id: str, request: Request, background_tasks: BackgroundTasks
) -> ReviewStarted:
    # Re-runs with whatever ReviewConfig the PM last chose for this doc via the web app —
    # the add-on has no settings form of its own.
    container = get_container(request)
    previous = container.repository.list_for_doc(doc_id, limit=1)
    if not previous:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Für dieses Dokument gibt es noch keinen Review. Bitte zuerst über die "
            "PM-Web-App starten.",
        )
    budget = container.settings.token_budget
    orchestrator = container.build_orchestrator(budget)
    run = orchestrator.create(doc_id, previous[0].config, budget)
    background_tasks.add_task(execute_in_background, orchestrator, run)
    return ReviewStarted(run_id=run.id, status=run.status)


@addon_router.get("/{doc_id}/runs/{run_id}/status")
def get_run_status(doc_id: str, run_id: UUID, request: Request) -> RunStatusResponse:
    container = get_container(request)
    try:
        run = container.repository.get(run_id)
    except RunNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lauf nicht gefunden."
        ) from error
    if run.doc_id != doc_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lauf nicht gefunden.")
    return RunStatusResponse(
        run_id=run.id,
        status=run.status,
        finding_count=run.finding_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@addon_router.post("/{doc_id}/findings/{key}/resolve")
def resolve_finding(doc_id: str, key: str, request: Request) -> ResolveResult:
    # Resolving is a direct, native Drive action (a reply with action=resolve) — no local
    # copy of the finding is kept anywhere (§9); the next /findings read simply omits it
    # because findings_from_comments skips resolved comments.
    container = get_container(request)
    source = container.build_comments_source()
    try:
        comments = source.read_comments(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    target_comment_id: str | None = None
    for comment in comments:
        if comment.resolved or comment.id is None:
            continue
        finding = parse_comment_body(comment.content)
        if finding is not None and finding_key(doc_id, finding) == key:
            target_comment_id = comment.id
            break
    if target_comment_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding nicht gefunden.")
    resolver = container.build_comment_resolver()
    resolver.resolve_comment(doc_id, target_comment_id)
    logger.info("resolved finding via add-on")
    return ResolveResult(key=key, resolved=True)
