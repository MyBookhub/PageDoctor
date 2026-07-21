from datetime import datetime
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from pagedoctor.app.addon_auth import require_addon_token
from pagedoctor.app.container import get_container
from pagedoctor.app.routes import execute_in_background
from pagedoctor.domain.errors import DocumentAccessDeniedError, RunNotFoundError
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.finding import Suggestion
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.services.comment_format import parse_comment_body
from pagedoctor.domain.services.idempotency import finding_key
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

_TERMINAL_STATUSES = frozenset({RunStatus.DONE, RunStatus.INCOMPLETE, RunStatus.FAILED})

addon_router = APIRouter(prefix="/docs", dependencies=[Depends(require_addon_token)])


class ResolveOutcome(StrEnum):
    APPLIED = "applied"
    DISMISSED = "dismissed"


class AddonFinding(BaseModel):
    key: str
    comment_id: str | None
    quote: str
    proposed_change: str
    reason_de: str


class DocFindings(BaseModel):
    doc_id: str
    findings: list[AddonFinding]


class AddonReviewConfig(BaseModel):
    modes: list[str]
    book_type: str
    strictness: str
    recipe_mode: bool = False
    custom_dictionary: list[str] = []


class LastConfig(BaseModel):
    modes: list[str]
    book_type: str
    strictness: str
    recipe_mode: bool
    custom_dictionary: list[str]


class DocState(BaseModel):
    doc_id: str
    latest_run_id: UUID | None
    latest_status: RunStatus | None
    latest_finding_count: int
    changed: bool
    last_reviewed: datetime | None
    last_config: LastConfig | None


class ReviewStarted(BaseModel):
    run_id: UUID
    status: RunStatus


class RunStatusResponse(BaseModel):
    run_id: UUID
    status: RunStatus
    done: bool
    finding_count: int
    started_at: datetime | None
    finished_at: datetime | None


class ResolveResult(BaseModel):
    comment_id: str
    resolved: bool


def to_addon_finding(doc_id: str, suggestion: Suggestion, comment_id: str | None) -> AddonFinding:
    return AddonFinding(
        key=finding_key(doc_id, suggestion),
        comment_id=comment_id,
        quote=suggestion.original_text,
        proposed_change=suggestion.proposed_change,
        reason_de=suggestion.reason_de,
    )


def to_last_config(config: ReviewConfig) -> LastConfig:
    return LastConfig(
        modes=sorted(mode.value for mode in config.modes),
        book_type=config.book_type.value,
        strictness=config.strictness.value,
        recipe_mode=config.recipe_mode,
        custom_dictionary=sorted(config.custom_dictionary.allowed_terms),
    )


def build_addon_review_config(payload: AddonReviewConfig) -> ReviewConfig:
    if not payload.modes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bitte mindestens einen Prüfmodus wählen.",
        )
    try:
        modes = frozenset(CheckMode(mode) for mode in payload.modes)
        book_type = BookType(payload.book_type)
        strictness = Strictness(payload.strictness)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Ungültige Auswahl."
        ) from error
    terms = frozenset(term.strip() for term in payload.custom_dictionary if term.strip())
    return ReviewConfig(
        modes=modes,
        book_type=book_type,
        strictness=strictness,
        custom_dictionary=CustomDictionary(allowed_terms=terms),
        recipe_mode=payload.recipe_mode,
    )


@addon_router.get("/{doc_id}/findings")
def get_doc_findings(doc_id: str, request: Request) -> DocFindings:
    # Always re-derived live from the Drive comments Sophie already posted — the add-on
    # has no separate copy of finding content anywhere (§9). "Syncing" is just calling this
    # endpoint again; a resolved comment naturally drops out.
    container = get_container(request)
    source = container.build_comments_source()
    try:
        comments = source.read_comments(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    findings: list[AddonFinding] = []
    for comment in comments:
        if comment.resolved:
            continue
        suggestion = parse_comment_body(comment.content)
        if suggestion is not None:
            findings.append(to_addon_finding(doc_id, suggestion, comment.id))
    logger.info("served add-on findings", extra={"finding_count": len(findings)})
    return DocFindings(doc_id=doc_id, findings=findings)


@addon_router.get("/{doc_id}/state")
def get_doc_state(doc_id: str, request: Request) -> DocState:
    container = get_container(request)
    previous = container.repository.list_for_doc(doc_id, limit=1)
    latest: ReviewRun | None = previous[0] if previous else None
    return DocState(
        doc_id=doc_id,
        latest_run_id=latest.id if latest else None,
        latest_status=latest.status if latest else None,
        latest_finding_count=latest.finding_count if latest else 0,
        # Revision-based change detection isn't built yet — always "unchanged" for now.
        # Tracked as a follow-up (see the "Findings by AI" issue); DocReviewState was
        # designed metadata-only (revision id + chunk hashes, never content) for this.
        changed=False,
        last_reviewed=(latest.finished_at or latest.started_at) if latest else None,
        last_config=to_last_config(latest.config) if latest else None,
    )


@addon_router.post("/{doc_id}/review")
def start_doc_review(
    doc_id: str,
    payload: AddonReviewConfig,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ReviewStarted:
    # The sidebar always sends its own settings form (book type, strictness, modes, recipe
    # mode, custom dictionary) — same shape as the PM web form, just as JSON.
    container = get_container(request)
    config = build_addon_review_config(payload)
    budget = container.settings.token_budget
    orchestrator = container.build_orchestrator(budget)
    run = orchestrator.create(doc_id, config, budget)
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
        done=run.status in _TERMINAL_STATUSES,
        finding_count=run.finding_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@addon_router.post("/{doc_id}/findings/{comment_id}/resolve")
def resolve_finding(
    doc_id: str, comment_id: str, outcome: ResolveOutcome, request: Request
) -> ResolveResult:
    # Resolving is a direct, native Drive action (a reply with action=resolve) — no local
    # copy of the finding is kept anywhere (§9); the next /findings read simply omits it.
    # `outcome` (applied/dismissed) is a UI action label, not manuscript content — logged
    # for a lightweight audit trail only, never persisted.
    container = get_container(request)
    source = container.build_comments_source()
    try:
        comments = source.read_comments(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    exists = any(comment.id == comment_id and not comment.resolved for comment in comments)
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding nicht gefunden.")
    resolver = container.build_comment_resolver()
    resolver.resolve_comment(doc_id, comment_id)
    logger.info("resolved finding via add-on", extra={"outcome": outcome})
    return ResolveResult(comment_id=comment_id, resolved=True)
