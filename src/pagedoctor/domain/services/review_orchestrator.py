import uuid
from collections.abc import Callable, Sequence
from datetime import timedelta
from uuid import UUID

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.doc_state import DocReviewState
from pagedoctor.domain.models.document import SourceDocument, TextChunk
from pagedoctor.domain.models.engine import EngineResult
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding
from pagedoctor.domain.ports.clock import ClockPort
from pagedoctor.domain.ports.comment_resolver import CommentResolverPort
from pagedoctor.domain.ports.comments_source import CommentsSourcePort
from pagedoctor.domain.ports.document_source import DocumentSourcePort
from pagedoctor.domain.ports.finding_repository import FindingRepositoryPort
from pagedoctor.domain.ports.output import OutputPort
from pagedoctor.domain.ports.run_repository import RunRepositoryPort
from pagedoctor.domain.services.chunker import chunk_document
from pagedoctor.domain.services.comment_format import findings_from_comments
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key
from pagedoctor.domain.services.incremental import changed_chunks, chunk_hashes
from pagedoctor.logging import get_logger, reset_correlation_id, set_correlation_id

logger = get_logger(__name__)


class ReviewOrchestrator:
    def __init__(
        self,
        source: DocumentSourcePort,
        engine: EditingEngine,
        output: OutputPort,
        repository: RunRepositoryPort,
        clock: ClockPort,
        comments_source: CommentsSourcePort,
        comment_resolver: CommentResolverPort,
        finding_repository: FindingRepositoryPort,
        findings_ttl_days: int = 90,
    ) -> None:
        self._source = source
        self._engine = engine
        self._output = output
        self._repository = repository
        self._clock = clock
        self._comments_source = comments_source
        self._comment_resolver = comment_resolver
        self._finding_repository = finding_repository
        self._findings_ttl_days = findings_ttl_days

    def create(
        self, doc_id: str, config: ReviewConfig, token_budget: int | None = None
    ) -> ReviewRun:
        # Persist a PENDING run and return immediately so the web layer can hand back a
        # run id and poll; the heavy execute() then runs in the background. started_at is
        # set here (submission time) so the runs list orders stably even before execution.
        run = ReviewRun(
            id=uuid.uuid4(),
            doc_id=doc_id,
            config=config,
            status=RunStatus.PENDING,
            started_at=self._clock.now(),
            correlation_id=uuid.uuid4().hex,
            token_budget=token_budget,
        )
        self._repository.save(run)
        return run

    def start(
        self, doc_id: str, config: ReviewConfig, token_budget: int | None = None
    ) -> ReviewRun:
        return self.execute(self.create(doc_id, config, token_budget))

    def resume(self, run_id: UUID) -> ReviewRun:
        run = self._repository.get(run_id)
        # A completed run is never reprocessed; its comments already stand in the doc.
        if run.status is RunStatus.DONE:
            return run
        return self.execute(run)

    def execute(self, run: ReviewRun) -> ReviewRun:
        return self.run_with_status(run, self.read_analyze_write)

    def execute_incremental(self, run: ReviewRun) -> ReviewRun:
        return self.run_with_status(run, self.incremental_read_analyze_write)

    def run_with_status(self, run: ReviewRun, work: Callable[[ReviewRun], ReviewRun]) -> ReviewRun:
        # Bind the run's correlation id so every downstream log (engine, source, output)
        # is traceable to this run; reset it after so it never leaks across runs/threads.
        token = set_correlation_id(run.correlation_id)
        try:
            running = run.model_copy(
                update={
                    "status": RunStatus.RUNNING,
                    "started_at": run.started_at or self._clock.now(),
                    "finished_at": None,
                }
            )
            self._repository.save(running)
            logger.info("review run started", extra={"run_id": str(running.id)})
            try:
                return work(running)
            except Exception:
                # Record the failure durably before it propagates, so a half-written doc is
                # never represented as a finished run; the boundary maps the raised error.
                failed = running.model_copy(
                    update={"status": RunStatus.FAILED, "finished_at": self._clock.now()}
                )
                self._repository.save(failed)
                logger.info("review run failed", extra={"run_id": str(failed.id)})
                raise
        finally:
            reset_correlation_id(token)

    def read_analyze_write(self, run: ReviewRun) -> ReviewRun:
        document = self._source.read(run.doc_id)
        result = self._engine.run(document, run.config)
        writing = run.model_copy(
            update={"status": RunStatus.WRITING, "finding_count": len(result.findings)}
        )
        self._repository.save(writing)
        self._output.write_findings(writing, result.findings, result.report)
        return self.checkpoint_completion(writing, result)

    def incremental_read_analyze_write(self, run: ReviewRun) -> ReviewRun:
        document = self._source.read(run.doc_id)
        all_chunks = chunk_document(document, run.config)
        chunks = self.chunks_to_review(run.doc_id, document, all_chunks)
        result = self._engine.run_chunks(document, run.config, chunks)
        writing = run.model_copy(
            update={"status": RunStatus.WRITING, "finding_count": len(result.findings)}
        )
        self._repository.save(writing)
        self._output.write_findings(writing, result.findings, result.report)
        # Persist the new fingerprint before the best-effort sync, so a failure syncing
        # findings can't cost the next pass a full re-review.
        self.save_review_state(document, all_chunks, run.config)
        self.sync_findings(writing, document)
        return self.checkpoint_completion(writing, result)

    def chunks_to_review(
        self, doc_id: str, document: SourceDocument, all_chunks: Sequence[TextChunk]
    ) -> list[TextChunk]:
        stored = self._repository.get_doc_state(doc_id)
        if stored is None:
            return list(all_chunks)
        if stored.revision_id is not None and stored.revision_id == document.revision_id:
            return []
        return changed_chunks(stored.chunk_hashes, all_chunks)

    def sync_findings(self, run: ReviewRun, document: SourceDocument) -> None:
        # The DB is the source of truth for findings (§9.2). Read the comments Sophie just
        # posted (they carry the real Drive comment ids), persist each to the DB, and resolve
        # any whose quoted text no longer appears — those are obsolete. Reading the comments
        # back also backfills findings posted before this store existed.
        now = self._clock.now()
        to_store: list[StoredFinding] = []
        for open_finding in findings_from_comments(
            self._comments_source.read_comments(document.doc_id)
        ):
            if open_finding.finding.suggestion.original_text in document.text:
                to_store.append(
                    StoredFinding(
                        key=finding_key(document.doc_id, open_finding.finding),
                        doc_id=document.doc_id,
                        run_id=run.id,
                        comment_id=open_finding.comment_id,
                        finding=open_finding.finding,
                        status=FindingStatus.OPEN,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                self._comment_resolver.resolve_comment(document.doc_id, open_finding.comment_id)
                self._finding_repository.set_status(
                    document.doc_id, open_finding.comment_id, FindingStatus.OBSOLETE
                )
        self._finding_repository.save_findings(to_store)
        self._finding_repository.purge_expired(now - timedelta(days=self._findings_ttl_days))

    def save_review_state(
        self, document: SourceDocument, all_chunks: Sequence[TextChunk], config: ReviewConfig
    ) -> None:
        self._repository.save_doc_state(
            DocReviewState(
                doc_id=document.doc_id,
                revision_id=document.revision_id,
                chunk_hashes=chunk_hashes(all_chunks),
                config=config,
                updated_at=self._clock.now(),
            )
        )

    def checkpoint_completion(self, run: ReviewRun, result: EngineResult) -> ReviewRun:
        posted = set(run.posted_finding_keys)
        posted.update(finding_key(run.doc_id, finding) for finding in result.findings)
        posted.add(consistency_report_key(run.doc_id))
        status = RunStatus.DONE if result.complete else RunStatus.INCOMPLETE
        completed = run.model_copy(
            update={
                "status": status,
                "finished_at": self._clock.now(),
                "posted_finding_keys": frozenset(posted),
            }
        )
        self._repository.save(completed)
        logger.info(
            "review run finished",
            extra={
                "run_id": str(completed.id),
                "status": status.value,
                "finding_count": completed.finding_count,
                "posted_key_count": len(posted),
            },
        )
        return completed
