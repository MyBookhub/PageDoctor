from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from pagedoctor.app.addon_auth import require_addon_token
from pagedoctor.app.container import get_container
from pagedoctor.domain.errors import DocumentAccessDeniedError, RunNotFoundError
from pagedoctor.domain.models.comment import OpenFinding
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.finding import Category, Priority
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.services.comment_format import findings_from_comments
from pagedoctor.domain.services.idempotency import finding_key
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

addon_router = APIRouter(prefix="/docs", dependencies=[Depends(require_addon_token)])

_TERMINAL = {RunStatus.DONE, RunStatus.INCOMPLETE, RunStatus.FAILED}


def review_in_background(orchestrator: ReviewOrchestrator, run: ReviewRun) -> None:
    # Incremental: the first pass reviews the whole doc and records its state; later passes
    # re-review only changed chunks. The orchestrator persists any failure as FAILED before
    # raising, so we swallow here to not crash the worker; log the error class only — never
    # exc_info, since a traceback could carry manuscript text (§9).
    try:
        orchestrator.execute_incremental(run)
    except Exception as error:
        logger.warning("add-on review failed for run %s (%s)", run.id, type(error).__name__)


class AddonFinding(BaseModel):
    key: str
    comment_id: str
    quote: str
    proposed_change: str
    reason_de: str
    category: Category
    priority: Priority


class DocFindings(BaseModel):
    doc_id: str
    findings: list[AddonFinding]


class ReviewRequest(BaseModel):
    modes: list[CheckMode]
    book_type: BookType
    strictness: Strictness
    recipe_mode: bool = False
    custom_dictionary: list[str] = []


class ReviewStarted(BaseModel):
    run_id: str
    status: RunStatus


class RunProgress(BaseModel):
    status: RunStatus
    finding_count: int
    done: bool


class ResolveResponse(BaseModel):
    resolved: bool


class DocState(BaseModel):
    reviewed: bool
    changed: bool


def to_addon_finding(doc_id: str, open_finding: OpenFinding) -> AddonFinding:
    finding = open_finding.finding
    suggestion = finding.suggestion
    return AddonFinding(
        key=finding_key(doc_id, finding),
        comment_id=open_finding.comment_id,
        quote=suggestion.original_text,
        proposed_change=suggestion.proposed_change,
        reason_de=suggestion.reason_de,
        category=finding.category,
        priority=finding.priority,
    )


def to_review_config(body: ReviewRequest) -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset(body.modes),
        book_type=body.book_type,
        strictness=body.strictness,
        recipe_mode=body.recipe_mode,
        custom_dictionary=CustomDictionary(allowed_terms=frozenset(body.custom_dictionary)),
    )


@addon_router.get("/{doc_id}/findings")
def get_doc_findings(doc_id: str, request: Request) -> DocFindings:
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
    return DocFindings(doc_id=doc_id, findings=[to_addon_finding(doc_id, of) for of in findings])


@addon_router.post("/{doc_id}/review")
def trigger_review(
    doc_id: str, body: ReviewRequest, request: Request, background_tasks: BackgroundTasks
) -> ReviewStarted:
    if not body.modes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bitte mindestens einen Prüfmodus auswählen.",
        )
    container = get_container(request)
    budget = container.settings.token_budget
    orchestrator = container.build_orchestrator(budget)
    run = orchestrator.create(doc_id, to_review_config(body), budget)
    background_tasks.add_task(review_in_background, orchestrator, run)
    return ReviewStarted(run_id=str(run.id), status=run.status)


@addon_router.get("/{doc_id}/runs/{run_id}/status")
def run_status(doc_id: str, run_id: UUID, request: Request) -> RunProgress:
    container = get_container(request)
    try:
        run = container.repository.get(run_id)
    except RunNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lauf nicht gefunden."
        ) from error
    if run.doc_id != doc_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lauf nicht gefunden.")
    return RunProgress(
        status=run.status, finding_count=run.finding_count, done=run.status in _TERMINAL
    )


@addon_router.post("/{doc_id}/findings/{comment_id}/resolve")
def resolve_finding(doc_id: str, comment_id: str, request: Request) -> ResolveResponse:
    container = get_container(request)
    try:
        container.build_comment_resolver().resolve_comment(doc_id, comment_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    return ResolveResponse(resolved=True)


@addon_router.get("/{doc_id}/state")
def doc_state(doc_id: str, request: Request) -> DocState:
    container = get_container(request)
    stored = container.repository.get_doc_state(doc_id)
    if stored is None:
        return DocState(reviewed=False, changed=False)
    try:
        current = container.build_document_source().read(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    changed = current.revision_id != stored.revision_id
    return DocState(reviewed=True, changed=changed)
