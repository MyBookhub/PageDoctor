import uuid
from collections.abc import Sequence

import pytest

from fakes.clock import FakeClock
from fakes.comments_source import FakeCommentsSource
from fakes.document_source import FakeDocumentSource
from fakes.llm import FakeLlmProvider
from fakes.output import FakeOutputPort
from fakes.run_repository import InMemoryRunRepository
from pagedoctor.domain.errors import CommentPostingError, RunNotFoundError
from pagedoctor.domain.models.comment import DocComment
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
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.services.comment_format import format_comment_body
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator
from pagedoctor.logging import get_correlation_id

DOC_ID = "doc-1"
DOC_TEXT = "Der Hund ist braun. Die Katze schläft tief."


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _document(text: str = DOC_TEXT, revision_id: str | None = None) -> SourceDocument:
    return SourceDocument(
        doc_id=DOC_ID,
        text=text,
        index_map=IndexMap(plain_text_length=len(text)),
        revision_id=revision_id,
    )


def _finding(quote: str) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=quote, proposed_change=f"{quote}!", reason_de="x"),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def _orchestrator(
    repository: InMemoryRunRepository,
    output: FakeOutputPort,
    provider: FakeLlmProvider,
    document: SourceDocument | None = None,
    comments_source: FakeCommentsSource | None = None,
) -> ReviewOrchestrator:
    source = FakeDocumentSource({DOC_ID: document or _document()})
    return ReviewOrchestrator(
        source=source,
        engine=EditingEngine(provider),
        output=output,
        repository=repository,
        clock=FakeClock(),
        comments_source=comments_source or FakeCommentsSource({DOC_ID: []}),
        comment_resolver=output,
    )


def _provider(*quotes: str) -> FakeLlmProvider:
    return FakeLlmProvider(responses={0: ChunkFindings(findings=[_finding(q) for q in quotes])})


def test_start_runs_end_to_end_and_marks_done() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()

    run = _orchestrator(repository, output, _provider("ist braun")).start(DOC_ID, _config())

    assert run.status is RunStatus.DONE
    assert run.finding_count == 1
    assert run.started_at is not None
    assert run.finished_at is not None
    # One finding comment plus the single consistency report.
    assert len(output.post_log) == 2


def test_completed_run_persists_in_repository() -> None:
    repository = InMemoryRunRepository()

    run = _orchestrator(repository, FakeOutputPort(), _provider("ist braun")).start(
        DOC_ID, _config()
    )

    stored = repository.get(run.id)
    assert stored.status is RunStatus.DONE
    assert stored.posted_finding_keys == run.posted_finding_keys


def test_killed_run_resumes_from_checkpoint_without_reposting() -> None:
    repository = InMemoryRunRepository()
    finding = _finding("ist braun")
    keys = frozenset({finding_key(DOC_ID, finding), consistency_report_key(DOC_ID)})
    # A run that posted everything but was killed before being marked done.
    killed = ReviewRun(
        id=uuid.uuid4(),
        doc_id=DOC_ID,
        config=_config(),
        status=RunStatus.WRITING,
        correlation_id="cid",
        finding_count=1,
        posted_finding_keys=keys,
    )
    repository.save(killed)
    output = FakeOutputPort()

    resumed = _orchestrator(repository, output, _provider("ist braun")).resume(killed.id)

    assert resumed.status is RunStatus.DONE
    # The checkpoint already covers every key, so nothing is posted again.
    assert output.post_log == []


def test_failure_mid_write_marks_failed_and_reraises() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort(fail_after=1)

    orchestrator = _orchestrator(repository, output, _provider("ist braun", "schläft tief"))
    with pytest.raises(CommentPostingError):
        orchestrator.start(DOC_ID, _config())

    stored = next(iter(repository._runs.values()))
    assert stored.status is RunStatus.FAILED
    assert len(output.post_log) == 1


def test_resume_after_mid_write_failure_does_not_double_post() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort(fail_after=1)
    orchestrator = _orchestrator(repository, output, _provider("ist braun", "schläft tief"))

    with pytest.raises(CommentPostingError):
        orchestrator.start(DOC_ID, _config())
    run_id = next(iter(repository._runs))
    posted_before = list(output.post_log)

    # The doc (FakeOutputPort instance) survives the crash; resume continues from it.
    output._fail_after = None
    resumed = orchestrator.resume(run_id)

    assert resumed.status is RunStatus.DONE
    # No key is ever posted twice across the original attempt and the resume.
    assert len(output.post_log) == len(set(output.post_log))
    assert output.post_log[: len(posted_before)] == posted_before


def test_budget_trip_marks_incomplete_never_done() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()
    big = _document("\n\n".join(f"Absatz {n} mit Inhalt zum Fuellen." for n in range(400)))
    provider = FakeLlmProvider(
        responses={0: ChunkFindings(findings=[_finding("Absatz 0 mit Inhalt")])},
        budget_after=1,
    )

    run = _orchestrator(repository, output, provider, document=big).start(DOC_ID, _config())

    assert run.status is RunStatus.INCOMPLETE
    # Partial findings are still posted (idempotently) before stopping.
    assert run.finding_count == 1


def test_resume_of_done_run_is_a_noop() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()
    orchestrator = _orchestrator(repository, output, _provider("ist braun"))
    done = orchestrator.start(DOC_ID, _config())
    posts_after_first = list(output.post_log)

    again = orchestrator.resume(done.id)

    assert again.status is RunStatus.DONE
    assert output.post_log == posts_after_first


def test_resume_unknown_run_raises() -> None:
    orchestrator = _orchestrator(InMemoryRunRepository(), FakeOutputPort(), _provider())
    with pytest.raises(RunNotFoundError):
        orchestrator.resume(uuid.uuid4())


def test_first_incremental_reviews_all_and_saves_state() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()
    provider = _provider("ist braun")
    orchestrator = _orchestrator(repository, output, provider, document=_document(revision_id="r1"))

    run = orchestrator.execute_incremental(orchestrator.create(DOC_ID, _config()))

    assert run.status is RunStatus.DONE
    assert len(provider.calls) >= 1
    state = repository.get_doc_state(DOC_ID)
    assert state is not None
    assert state.revision_id == "r1"


def test_incremental_skips_llm_when_revision_is_unchanged() -> None:
    repository = InMemoryRunRepository()
    first = _orchestrator(
        repository, FakeOutputPort(), _provider("ist braun"), document=_document(revision_id="r1")
    )
    first.execute_incremental(first.create(DOC_ID, _config()))

    provider = _provider("ist braun")
    again = _orchestrator(
        repository, FakeOutputPort(), provider, document=_document(revision_id="r1")
    )
    run = again.execute_incremental(again.create(DOC_ID, _config()))

    assert run.status is RunStatus.DONE
    assert provider.calls == []


def test_incremental_reviews_again_when_text_changed() -> None:
    repository = InMemoryRunRepository()
    first = _orchestrator(
        repository, FakeOutputPort(), _provider("ist braun"), document=_document(revision_id="r1")
    )
    first.execute_incremental(first.create(DOC_ID, _config()))

    changed = _document("Der Hund ist grün. Die Katze schläft tief.", revision_id="r2")
    provider = _provider("ist grün")
    again = _orchestrator(repository, FakeOutputPort(), provider, document=changed)
    again.execute_incremental(again.create(DOC_ID, _config()))

    assert len(provider.calls) >= 1


def test_incremental_resolves_findings_whose_text_is_gone() -> None:
    repository = InMemoryRunRepository()
    output = FakeOutputPort()
    gone = _finding("ein Satz der nicht mehr existiert")
    comment = DocComment(
        id="cX", content=format_comment_body(gone, finding_key(DOC_ID, gone)), resolved=False
    )
    comments = FakeCommentsSource({DOC_ID: [comment]})
    orchestrator = _orchestrator(
        repository,
        output,
        _provider("ist braun"),
        document=_document(revision_id="r1"),
        comments_source=comments,
    )

    orchestrator.execute_incremental(orchestrator.create(DOC_ID, _config()))

    assert "cX" in output.resolved


def test_run_binds_correlation_id_for_downstream_logs_then_resets() -> None:
    seen: list[str] = []

    class CapturingOutput:
        def write_findings(
            self,
            run: ReviewRun,
            findings: Sequence[Finding],
            report: ConsistencyReport,
        ) -> None:
            seen.append(get_correlation_id())

    repository = InMemoryRunRepository()
    orchestrator = ReviewOrchestrator(
        source=FakeDocumentSource({DOC_ID: _document()}),
        engine=EditingEngine(_provider("ist braun")),
        output=CapturingOutput(),
        repository=repository,
        clock=FakeClock(),
        comments_source=FakeCommentsSource({DOC_ID: []}),
        comment_resolver=FakeOutputPort(),
    )

    run = orchestrator.start(DOC_ID, _config())

    # Downstream work runs under the run's correlation id, not the default "-".
    assert seen == [run.correlation_id]
    assert seen[0] != "-"
    # The context var is reset after the run, so it never leaks into later work.
    assert get_correlation_id() == "-"
