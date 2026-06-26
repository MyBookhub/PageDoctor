from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReviewRunRow(Base):
    # Metadata only (CLAUDE.md §9): no column ever holds manuscript or finding text.
    # `config` carries review settings; `posted_finding_keys` carries one-way hashes.
    __tablename__ = "review_runs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    posted_finding_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    token_budget: Mapped[int | None] = mapped_column(Integer)


class DocReviewStateRow(Base):
    # Metadata only (CLAUDE.md §9): per-doc change-detection fingerprints, never content.
    # `chunk_hashes` are one-way hashes; `config` carries review settings only.
    __tablename__ = "doc_review_states"

    doc_id: Mapped[str] = mapped_column(String, primary_key=True)
    revision_id: Mapped[str | None] = mapped_column(String)
    chunk_hashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
