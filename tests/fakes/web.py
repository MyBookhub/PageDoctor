from dataclasses import dataclass

from fakes.clock import FakeClock
from fakes.comments_source import FakeCommentsSource
from fakes.document_source import FakeDocumentSource
from fakes.finding_repository import InMemoryFindingRepository
from fakes.llm import FakeLlmProvider
from fakes.output import FakeOutputPort
from fakes.run_repository import InMemoryRunRepository
from pagedoctor.app.container import Container
from pagedoctor.config import Settings
from pagedoctor.domain.models.document import IndexMap, SourceDocument
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.ports.comment_resolver import CommentResolverPort
from pagedoctor.domain.ports.comments_source import CommentsSourcePort
from pagedoctor.domain.ports.document_source import DocumentSourcePort
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator

DOC_ID = "testdoc0000000000001"
DOC_TEXT = "Der Hund ist braun. Die Katze schläft tief im Korb."


def fake_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_secret_key": "test-secret-key",
        "database_url": "postgresql+psycopg://test/test",
        "anthropic_api_key": "test-anthropic-key",
        "google_service_account_file": "/tmp/sophie.json",
        "finding_encryption_key": "hqRJtL1uKChplt01KMGr1zMQqQ9R1xiRa8139J3lo6U=",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def _default_provider() -> FakeLlmProvider:
    finding = Finding(
        suggestion=Suggestion(
            original_text="ist braun", proposed_change="ist dunkelbraun", reason_de="Präziser."
        ),
        category=Category.PROOFREADING,
        priority=Priority.EMPFEHLUNG,
    )
    return FakeLlmProvider(default=ChunkFindings(findings=[finding]))


@dataclass
class FakeWeb:
    container: Container
    repository: InMemoryRunRepository
    finding_repository: InMemoryFindingRepository
    output: FakeOutputPort
    provider: FakeLlmProvider


def build_fake_web(
    output: FakeOutputPort | None = None,
    provider: FakeLlmProvider | None = None,
    settings: Settings | None = None,
    comments_source: CommentsSourcePort | None = None,
) -> FakeWeb:
    repository = InMemoryRunRepository()
    finding_repository = InMemoryFindingRepository()
    shared_output = output or FakeOutputPort()
    shared_provider = provider or _default_provider()
    shared_comments = comments_source or FakeCommentsSource({DOC_ID: []})
    document = SourceDocument(
        doc_id=DOC_ID, text=DOC_TEXT, index_map=IndexMap(plain_text_length=len(DOC_TEXT))
    )
    source = FakeDocumentSource({DOC_ID: document})

    def build_orchestrator(token_budget: int | None) -> ReviewOrchestrator:
        return ReviewOrchestrator(
            source=source,
            engine=EditingEngine(shared_provider),
            output=shared_output,
            repository=repository,
            clock=FakeClock(),
            comments_source=shared_comments,
            comment_resolver=shared_output,
            finding_repository=finding_repository,
        )

    def build_comments_source() -> CommentsSourcePort:
        return shared_comments

    def build_comment_resolver() -> CommentResolverPort:
        return shared_output

    def build_document_source() -> DocumentSourcePort:
        return source

    container = Container(
        settings=settings or fake_settings(),
        repository=repository,
        finding_repository=finding_repository,
        build_orchestrator=build_orchestrator,
        build_comments_source=build_comments_source,
        build_comment_resolver=build_comment_resolver,
        build_document_source=build_document_source,
    )
    return FakeWeb(container, repository, finding_repository, shared_output, shared_provider)
