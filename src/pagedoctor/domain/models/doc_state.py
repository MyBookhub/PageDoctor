from datetime import datetime

from pydantic import BaseModel, ConfigDict

from pagedoctor.domain.models.config import ReviewConfig


class DocReviewState(BaseModel):
    # Metadata only (data protection): per-doc change-detection fingerprints, never content.
    model_config = ConfigDict(frozen=True)

    doc_id: str
    revision_id: str | None
    chunk_hashes: frozenset[str]
    config: ReviewConfig
    updated_at: datetime
