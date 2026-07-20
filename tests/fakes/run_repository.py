from datetime import UTC, datetime
from uuid import UUID

from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.run import ReviewRun

_EPOCH = datetime.min.replace(tzinfo=UTC)


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[UUID, ReviewRun] = {}
        self.save_count = 0

    def save(self, run: ReviewRun) -> None:
        self.save_count += 1
        self._runs[run.id] = run

    def get(self, run_id: UUID) -> ReviewRun:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(str(run_id))
        return run

    def list_recent(self, limit: int = 50) -> list[ReviewRun]:
        ordered = sorted(
            self._runs.values(), key=lambda run: run.started_at or _EPOCH, reverse=True
        )
        return ordered[:limit]

    def list_for_doc(self, doc_id: str, limit: int = 20) -> list[ReviewRun]:
        matching = [run for run in self._runs.values() if run.doc_id == doc_id]
        ordered = sorted(matching, key=lambda run: run.started_at or _EPOCH, reverse=True)
        return ordered[:limit]
