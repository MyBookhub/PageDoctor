from collections.abc import Sequence

import pytest

from fakes.clock import FakeClock
from fakes.document_source import FakeDocumentSource
from fakes.llm import FakeLlmProvider
from fakes.output import FakeOutputPort
from fakes.run_repository import InMemoryRunRepository
from pagedoctor.domain.errors import CommentPostingError
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.document import IndexMap, SourceDocument
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.models.run import OutputResult, ReviewRun, RunStatus
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator

DOC_ID = "doc-42"
DOC_TEXT = "Der Hund ist braun. Die Katze schläft tief im Korb."
SECRET_QUOTE = "ist braun"
SECRET_CHANGE = "ist dunkelbraun"


class NullOutputPort:
    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> OutputResult:
        return OutputResult()


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING, CheckMode.EDITING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _document() -> SourceDocument:
    return SourceDocument(
        doc_id=DOC_ID, text=DOC_TEXT, index_map=IndexMap(plain_text_length=len(DOC_TEXT))
    )


def _provider() -> FakeLlmProvider:
    finding = Finding(
        suggestion=Suggestion(
            original_text=SECRET_QUOTE, proposed_change=SECRET_CHANGE, reason_de="Präziser."
        ),
        category=Category.PROOFREADING,
        priority=Priority.EMPFEHLUNG,
    )
    return FakeLlmProvider(responses={0: ChunkFindings(findings=[finding])})


def _orchestrator(
    repository: InMemoryRunRepository,
    output: FakeOutputPort | NullOutputPort,
    provider: FakeLlmProvider | None = None,
    source: FakeDocumentSource | None = None,
) -> ReviewOrchestrator:
    return ReviewOrchestrator(
        source=source or FakeDocumentSource({DOC_ID: _document()}),
        engine=EditingEngine(provider or _provider()),
        output=output,
        repository=repository,
        clock=FakeClock(),
    )


def test_full_flow_reads_analyzes_and_writes() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()
    source = FakeDocumentSource({DOC_ID: _document()})

    run = _orchestrator(repository, output, source=source).start(DOC_ID, _config())

    assert run.status is RunStatus.DONE
    assert source.reads == [DOC_ID]  # the doc is read fresh, exactly once
    assert run.finding_count == 1
    assert len(output.post_log) == 2  # one finding + the consistency report


def test_persisted_run_holds_no_manuscript_or_finding_text() -> None:
    repository = InMemoryRunRepository()

    run = _orchestrator(repository, FakeOutputPort()).start(DOC_ID, _config())

    serialized = repository.get(run.id).model_dump_json()
    assert DOC_TEXT not in serialized
    assert SECRET_QUOTE not in serialized
    assert SECRET_CHANGE not in serialized


def test_swapping_output_port_changes_only_output() -> None:
    via_comments = _orchestrator(InMemoryRunRepository(), FakeOutputPort()).start(DOC_ID, _config())
    via_null = _orchestrator(InMemoryRunRepository(), NullOutputPort()).start(DOC_ID, _config())

    # The engine, persona, modes and checkpoint are identical regardless of the output adapter.
    assert via_comments.status is via_null.status is RunStatus.DONE
    assert via_comments.finding_count == via_null.finding_count
    assert via_comments.posted_finding_keys == via_null.posted_finding_keys


def test_restart_mid_write_never_double_posts_and_completes() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort(fail_after=1)
    orchestrator = _orchestrator(repository, output)

    with pytest.raises(CommentPostingError):
        orchestrator.start(DOC_ID, _config())
    run_id = next(iter(repository._runs))
    assert repository.get(run_id).status is RunStatus.FAILED

    output._fail_after = None  # the Drive doc survives the crash; the process restarts
    resumed = orchestrator.resume(run_id)

    assert resumed.status is RunStatus.DONE
    assert len(output.post_log) == len(set(output.post_log))


def test_interrupted_run_is_never_marked_done() -> None:
    repository = InMemoryRunRepository()
    orchestrator = _orchestrator(repository, FakeOutputPort(fail_after=0))

    with pytest.raises(CommentPostingError):
        orchestrator.start(DOC_ID, _config())

    stored = next(iter(repository._runs.values()))
    assert stored.status is RunStatus.FAILED
    assert stored.finished_at is not None
