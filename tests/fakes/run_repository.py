from uuid import UUID

from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.run import ReviewRun


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
