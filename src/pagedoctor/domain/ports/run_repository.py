from typing import Protocol
from uuid import UUID

from pagedoctor.domain.models.run import ReviewRun


class RunRepositoryPort(Protocol):
    # Metadata only: never persists manuscript or finding text.
    # Raises RepositoryError on backend failure (defined by the persistence adapter).
    def save(self, run: ReviewRun) -> None: ...
    def get(self, run_id: UUID) -> ReviewRun: ...
