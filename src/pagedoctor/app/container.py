from collections.abc import Callable
from dataclasses import dataclass

import anthropic
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pagedoctor.adapters.clock import SystemClock
from pagedoctor.adapters.google.auth import build_docs_service, build_drive_service
from pagedoctor.adapters.google.comments_output import CommentsOutputAdapter
from pagedoctor.adapters.google.docs_source import GoogleDocsSource
from pagedoctor.adapters.llm.anthropic_provider import AnthropicLlmProvider
from pagedoctor.adapters.persistence.run_repository import PostgresRunRepository
from pagedoctor.config import Settings
from pagedoctor.domain.ports.run_repository import RunRepositoryPort
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator


@dataclass(frozen=True)
class Container:
    settings: Settings
    repository: RunRepositoryPort
    build_orchestrator: Callable[[int | None], ReviewOrchestrator]


def get_container(request: Request) -> Container:
    container = request.app.state.container
    if not isinstance(container, Container):
        raise RuntimeError("application container is not initialised")
    return container


def build_container(settings: Settings) -> Container:
    # Shared, thread-safe singletons. The Anthropic HTTP client and the SQLAlchemy pool are
    # safe to reuse across concurrent runs; the per-run adapters below are not.
    session_factory = sessionmaker(bind=create_engine(settings.database_url))
    repository = PostgresRunRepository(session_factory)
    clock = SystemClock()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    def build_orchestrator(token_budget: int | None) -> ReviewOrchestrator:
        # Built fresh per submission: the Google services are httplib2-backed (not
        # thread-safe) and the LLM provider carries a per-run token counter.
        provider = AnthropicLlmProvider(
            client, settings.anthropic_model, settings.anthropic_effort, token_budget
        )
        return ReviewOrchestrator(
            source=GoogleDocsSource(build_docs_service(settings)),
            engine=EditingEngine(provider),
            output=CommentsOutputAdapter(build_drive_service(settings)),
            repository=repository,
            clock=clock,
        )

    return Container(
        settings=settings, repository=repository, build_orchestrator=build_orchestrator
    )
