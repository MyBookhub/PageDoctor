import uuid

import pytest

from fakes.document_source import FakeDocumentSource
from fakes.llm import FakeLlmProvider
from fakes.output import FakeOutputPort
from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.document import IndexMap, SourceDocument, TextChunk
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.ports.document_source import DocumentSourcePort
from pagedoctor.domain.ports.llm_provider import LlmProviderPort
from pagedoctor.domain.ports.output import OutputPort


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _finding() -> Finding:
    return Finding(
        suggestion=Suggestion(original_text="Rezpet", proposed_change="Rezept", reason_de="x"),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def _run() -> ReviewRun:
    return ReviewRun(
        id=uuid.UUID(int=1),
        doc_id="doc-1",
        config=_config(),
        status=RunStatus.WRITING,
        correlation_id="cid",
    )


def _empty_report() -> ConsistencyReport:
    return ConsistencyReport(term_variants=[], spelling_variants=[], repetition_stats=[])


def test_fake_satisfies_port_and_scripts_findings() -> None:
    finding = _finding()
    provider: LlmProviderPort = FakeLlmProvider(responses={0: ChunkFindings(findings=[finding])})
    chunk = TextChunk(index=0, text="Rezpet", start_offset=0, end_offset=6)
    assert provider.analyze(chunk, _config()).findings == [finding]


def test_fake_document_source_returns_and_denies() -> None:
    document = SourceDocument(doc_id="doc-1", text="Hallo", index_map=IndexMap(plain_text_length=5))
    source: DocumentSourcePort = FakeDocumentSource({"doc-1": document})

    assert source.read("doc-1") is document
    with pytest.raises(DocumentAccessDeniedError):
        source.read("unknown")


def test_fake_output_port_is_idempotent() -> None:
    fake = FakeOutputPort()
    output: OutputPort = fake

    output.write_findings(_run(), [_finding()], _empty_report())
    after_first = dict(fake.posted)

    output.write_findings(_run(), [_finding()], _empty_report())

    assert fake.posted == after_first
