from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from pagedoctor.app.addon_routes import addon_router
from pagedoctor.app.container import Container, build_container
from pagedoctor.app.errors import InvalidReviewForm
from pagedoctor.app.routes import router, templates
from pagedoctor.config import load_settings
from pagedoctor.domain.errors import (
    DocumentAccessDeniedError,
    PageDoctorError,
    RunNotFoundError,
)
from pagedoctor.logging import configure_logging, get_logger

_STATIC_DIR = Path(__file__).parent / "static"


class HealthStatus(BaseModel):
    status: str


def error_response(request: Request, message: str, status_code: int) -> HTMLResponse:
    # HTMX requests get a bare fragment to swap in place; a direct navigation gets a page.
    name = "error.html" if request.headers.get("HX-Request") else "error_page.html"
    return templates.TemplateResponse(request, name, {"message": message}, status_code=status_code)


async def handle_run_not_found(request: Request, exc: Exception) -> HTMLResponse:
    return error_response(request, "Lauf nicht gefunden.", 404)


async def handle_access_denied(request: Request, exc: Exception) -> HTMLResponse:
    return error_response(request, "Auf das Dokument kann nicht zugegriffen werden.", 403)


async def handle_invalid_form(request: Request, exc: Exception) -> HTMLResponse:
    return error_response(request, str(exc), 422)


async def handle_pagedoctor_error(request: Request, exc: Exception) -> HTMLResponse:
    return error_response(request, "Etwas ist schiefgelaufen. Bitte erneut versuchen.", 500)


def create_app(container: Container | None = None) -> FastAPI:
    settings = container.settings if container is not None else load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        app.state.settings = settings
        app.state.container = container if container is not None else build_container(settings)
        get_logger(__name__).info("application started env=%s", settings.app_env)
        yield

    app = FastAPI(title="PageDoctor", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key.get_secret_value(),
        # Send the session/CSRF cookie only over HTTPS in production; kept off in dev so the
        # form works over local HTTP.
        https_only=settings.app_env == "production",
    )
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(router)
    app.include_router(addon_router)

    app.add_exception_handler(RunNotFoundError, handle_run_not_found)
    app.add_exception_handler(DocumentAccessDeniedError, handle_access_denied)
    app.add_exception_handler(InvalidReviewForm, handle_invalid_form)
    app.add_exception_handler(PageDoctorError, handle_pagedoctor_error)

    @app.get("/healthz")
    async def healthz() -> HealthStatus:
        return HealthStatus(status="ok")

    return app
