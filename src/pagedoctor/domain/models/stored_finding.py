from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from pagedoctor.domain.models.finding import Finding


class FindingStatus(StrEnum):
    OPEN = "open"
    APPLIED = "applied"
    DISMISSED = "dismissed"
    OBSOLETE = "obsolete"


class StoredFinding(BaseModel):
    # The persisted record of one Sophie finding. Its quote/proposed/reason are manuscript
    # excerpts and are stored encrypted at rest by the repository adapter (§9.2); the domain
    # only ever handles the plaintext model.
    model_config = ConfigDict(frozen=True)

    key: str
    doc_id: str
    run_id: UUID
    comment_id: str | None
    finding: Finding
    status: FindingStatus
    created_at: datetime
    updated_at: datetime
