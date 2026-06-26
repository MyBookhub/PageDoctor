from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pagedoctor.adapters.persistence.models import DocReviewStateRow, ReviewRunRow
from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.doc_state import DocReviewState
from pagedoctor.domain.models.run import ReviewRun, RunStatus


class PostgresRunRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, run: ReviewRun) -> None:
        with self._session_factory() as session, session.begin():
            session.merge(to_row(run))

    def get(self, run_id: UUID) -> ReviewRun:
        with self._session_factory() as session:
            row = session.get(ReviewRunRow, run_id)
            if row is None:
                raise RunNotFoundError(str(run_id))
            return to_domain(row)

    def list_recent(self, limit: int = 50) -> list[ReviewRun]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ReviewRunRow).order_by(ReviewRunRow.started_at.desc()).limit(limit)
            )
            return [to_domain(row) for row in rows]

    def get_doc_state(self, doc_id: str) -> DocReviewState | None:
        with self._session_factory() as session:
            row = session.get(DocReviewStateRow, doc_id)
            return doc_state_to_domain(row) if row is not None else None

    def save_doc_state(self, state: DocReviewState) -> None:
        with self._session_factory() as session, session.begin():
            session.merge(doc_state_to_row(state))


def to_row(run: ReviewRun) -> ReviewRunRow:
    return ReviewRunRow(
        id=run.id,
        doc_id=run.doc_id,
        config=run.config.model_dump(mode="json"),
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        finding_count=run.finding_count,
        correlation_id=run.correlation_id,
        posted_finding_keys=sorted(run.posted_finding_keys),
        token_budget=run.token_budget,
    )


def to_domain(row: ReviewRunRow) -> ReviewRun:
    return ReviewRun(
        id=row.id,
        doc_id=row.doc_id,
        config=ReviewConfig.model_validate(row.config),
        status=RunStatus(row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        finding_count=row.finding_count,
        correlation_id=row.correlation_id,
        posted_finding_keys=frozenset(row.posted_finding_keys),
        token_budget=row.token_budget,
    )


def doc_state_to_row(state: DocReviewState) -> DocReviewStateRow:
    return DocReviewStateRow(
        doc_id=state.doc_id,
        revision_id=state.revision_id,
        chunk_hashes=sorted(state.chunk_hashes),
        config=state.config.model_dump(mode="json"),
        updated_at=state.updated_at,
    )


def doc_state_to_domain(row: DocReviewStateRow) -> DocReviewState:
    return DocReviewState(
        doc_id=row.doc_id,
        revision_id=row.revision_id,
        chunk_hashes=frozenset(row.chunk_hashes),
        config=ReviewConfig.model_validate(row.config),
        updated_at=row.updated_at,
    )
