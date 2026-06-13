from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from pagedoctor.config import load_settings
from pagedoctor.logging import configure_logging, get_logger


class HealthStatus(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Fail fast: a missing required setting raises ConfigError here, before the app
    # accepts any request. Settings flow through app.state, not a module global.
    settings = load_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    get_logger(__name__).info(
        "application started env=%s port=%s", settings.app_env, settings.app_port
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PageDoctor", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> HealthStatus:
        return HealthStatus(status="ok")

    return app


app = create_app()
