from typing import Protocol
from uuid import UUID

from pagedoctor.domain.models.run import ReviewRun


class RunRepositoryPort(Protocol):
    def save(self, run: ReviewRun) -> None: ...
    def get(self, run_id: UUID) -> ReviewRun: ...
