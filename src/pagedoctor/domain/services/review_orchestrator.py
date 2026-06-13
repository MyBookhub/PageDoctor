import uuid
from uuid import UUID

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.engine import EngineResult
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.ports.clock import ClockPort
from pagedoctor.domain.ports.document_source import DocumentSourcePort
from pagedoctor.domain.ports.output import OutputPort
from pagedoctor.domain.ports.run_repository import RunRepositoryPort
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key
from pagedoctor.logging import get_logger

logger = get_logger(__name__)


class ReviewOrchestrator:
    def __init__(
        self,
        source: DocumentSourcePort,
        engine: EditingEngine,
        output: OutputPort,
        repository: RunRepositoryPort,
        clock: ClockPort,
    ) -> None:
        self._source = source
        self._engine = engine
        self._output = output
        self._repository = repository
        self._clock = clock

    def start(
        self, doc_id: str, config: ReviewConfig, token_budget: int | None = None
    ) -> ReviewRun:
        run = ReviewRun(
            id=uuid.uuid4(),
            doc_id=doc_id,
            config=config,
            status=RunStatus.PENDING,
            correlation_id=uuid.uuid4().hex,
            token_budget=token_budget,
        )
        self._repository.save(run)
        return self.execute(run)

    def resume(self, run_id: UUID) -> ReviewRun:
        run = self._repository.get(run_id)
        # A completed run is never reprocessed; its comments already stand in the doc.
        if run.status is RunStatus.DONE:
            return run
        return self.execute(run)

    def execute(self, run: ReviewRun) -> ReviewRun:
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
            return self.read_analyze_write(running)
        except Exception:
            # Record the failure durably before it propagates, so a half-written doc is
            # never represented as a finished run; the boundary maps the raised error.
            failed = running.model_copy(
                update={"status": RunStatus.FAILED, "finished_at": self._clock.now()}
            )
            self._repository.save(failed)
            logger.info("review run failed", extra={"run_id": str(failed.id)})
            raise

    def read_analyze_write(self, run: ReviewRun) -> ReviewRun:
        document = self._source.read(run.doc_id)
        result = self._engine.run(document, run.config)
        writing = run.model_copy(
            update={"status": RunStatus.WRITING, "finding_count": len(result.findings)}
        )
        self._repository.save(writing)
        self._output.write_findings(writing, result.findings, result.report)
        return self.checkpoint_completion(writing, result)

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
