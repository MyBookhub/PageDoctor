from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from pagedoctor.domain.models.config import ReviewConfig


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WRITING = "writing"
    DONE = "done"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class ReviewRun(BaseModel):
    # Metadata only: never holds manuscript or finding text (data protection).
    id: UUID
    doc_id: str
    config: ReviewConfig
    status: RunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    finding_count: int = 0
    correlation_id: str
    posted_finding_keys: frozenset[str] = frozenset()
    token_budget: int | None = None
