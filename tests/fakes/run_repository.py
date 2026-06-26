from datetime import UTC, datetime
from uuid import UUID

from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.doc_state import DocReviewState
from pagedoctor.domain.models.run import ReviewRun

_EPOCH = datetime.min.replace(tzinfo=UTC)


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[UUID, ReviewRun] = {}
        self._doc_states: dict[str, DocReviewState] = {}
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

    def get_doc_state(self, doc_id: str) -> DocReviewState | None:
        return self._doc_states.get(doc_id)

    def save_doc_state(self, state: DocReviewState) -> None:
        self._doc_states[state.doc_id] = state
