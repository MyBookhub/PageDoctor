from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pagedoctor.app.auth import require_auth, verify_csrf
from pagedoctor.app.container import Container
from pagedoctor.app.doc_url import parse_doc_id
from pagedoctor.app.errors import InvalidReviewForm
from pagedoctor.app.view_models import form_context, progress_context, runs_context
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.run import ReviewRun
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

router = APIRouter(dependencies=[Depends(require_auth)])


def get_container(request: Request) -> Container:
    container = request.app.state.container
    assert isinstance(container, Container)
    return container


def execute_in_background(orchestrator: ReviewOrchestrator, run: ReviewRun) -> None:
    try:
        orchestrator.execute(run)
    except Exception:
        # The orchestrator has already persisted the run as FAILED; the UI surfaces it via
        # the progress poll. Swallow here so a background failure can't crash the worker.
        logger.info("background review run failed")


def resume_in_background(orchestrator: ReviewOrchestrator, run_id: UUID) -> None:
    try:
        orchestrator.resume(run_id)
    except Exception:
        logger.info("background review resume failed")


def build_review_config(
    modes: Sequence[str],
    book_type: str,
    strictness: str,
    custom_dictionary: str,
    recipe_mode: bool,
) -> ReviewConfig:
    if not modes:
        raise InvalidReviewForm("Bitte mindestens einen Prüfmodus auswählen.")
    try:
        check_modes = frozenset(CheckMode(mode) for mode in modes)
        chosen_book_type = BookType(book_type)
        chosen_strictness = Strictness(strictness)
    except ValueError as error:
        raise InvalidReviewForm("Ungültige Auswahl im Formular.") from error
    terms = frozenset(
        term.strip() for term in custom_dictionary.replace(",", "\n").splitlines() if term.strip()
    )
    return ReviewConfig(
        modes=check_modes,
        book_type=chosen_book_type,
        strictness=chosen_strictness,
        custom_dictionary=CustomDictionary(allowed_terms=terms),
        recipe_mode=recipe_mode,
    )


@router.get("/", response_class=HTMLResponse)
async def review_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "review_form.html", form_context(request))


@router.post("/review", response_class=HTMLResponse)
async def submit_review(
    request: Request,
    background_tasks: BackgroundTasks,
    doc_url: Annotated[str, Form()],
    book_type: Annotated[str, Form()],
    strictness: Annotated[str, Form()],
    modes: Annotated[list[str] | None, Form()] = None,
    custom_dictionary: Annotated[str, Form()] = "",
    recipe_mode: Annotated[bool, Form()] = False,
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse:
    container = get_container(request)
    try:
        verify_csrf(request, csrf_token)
        doc_id = parse_doc_id(doc_url)
        config = build_review_config(
            modes or [], book_type, strictness, custom_dictionary, recipe_mode
        )
    except InvalidReviewForm as error:
        return templates.TemplateResponse(
            request, "error.html", {"message": str(error)}, status_code=422
        )
    budget = container.settings.token_budget
    orchestrator = container.build_orchestrator(budget)
    run = orchestrator.create(doc_id, config, budget)
    background_tasks.add_task(execute_in_background, orchestrator, run)
    return templates.TemplateResponse(request, "progress.html", progress_context(run))


@router.get("/runs", response_class=HTMLResponse)
async def list_runs(request: Request) -> HTMLResponse:
    container = get_container(request)
    runs = container.repository.list_recent()
    return templates.TemplateResponse(request, "runs.html", runs_context(request, runs))


@router.get("/runs/{run_id}/progress", response_class=HTMLResponse)
async def run_progress(request: Request, run_id: UUID) -> HTMLResponse:
    container = get_container(request)
    run = container.repository.get(run_id)
    return templates.TemplateResponse(request, "progress.html", progress_context(run))


@router.post("/runs/{run_id}/resume", response_class=HTMLResponse)
async def resume_run(
    request: Request,
    run_id: UUID,
    background_tasks: BackgroundTasks,
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse:
    container = get_container(request)
    verify_csrf(request, csrf_token)
    run = container.repository.get(run_id)
    orchestrator = container.build_orchestrator(run.token_budget)
    background_tasks.add_task(resume_in_background, orchestrator, run_id)
    return templates.TemplateResponse(request, "progress.html", progress_context(run))
