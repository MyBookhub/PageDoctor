from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from pagedoctor.adapters.persistence.crypto import FindingCipher
from pagedoctor.adapters.persistence.models import FindingRow
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding


class PostgresFindingRepository:
    def __init__(self, session_factory: sessionmaker[Session], cipher: FindingCipher) -> None:
        self._session_factory = session_factory
        self._cipher = cipher

    def save_findings(self, findings: Sequence[StoredFinding]) -> None:
        if not findings:
            return
        rows = [self.to_row(finding) for finding in findings]
        with self._session_factory() as session, session.begin():
            # Insert-if-absent: a re-review re-saves the same finding; keep the stored row
            # (and its status) rather than resetting an applied/dismissed finding to open.
            statement = insert(FindingRow).on_conflict_do_nothing(
                index_elements=[FindingRow.doc_id, FindingRow.key]
            )
            session.execute(statement, rows)

    def open_findings(self, doc_id: str) -> list[StoredFinding]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(FindingRow).where(
                    FindingRow.doc_id == doc_id,
                    FindingRow.status == FindingStatus.OPEN.value,
                )
            )
            return [self.to_domain(row) for row in rows]

    def set_status(self, doc_id: str, comment_id: str, status: FindingStatus) -> None:
        with self._session_factory() as session, session.begin():
            session.execute(
                update(FindingRow)
                .where(FindingRow.doc_id == doc_id, FindingRow.comment_id == comment_id)
                .values(status=status.value)
            )

    def purge_expired(self, cutoff: datetime) -> int:
        with self._session_factory() as session, session.begin():
            rows = session.scalars(select(FindingRow).where(FindingRow.updated_at < cutoff)).all()
            for row in rows:
                session.delete(row)
            return len(rows)

    def to_row(self, finding: StoredFinding) -> dict[str, object]:
        suggestion = finding.finding.suggestion
        return {
            "doc_id": finding.doc_id,
            "key": finding.key,
            "run_id": finding.run_id,
            "comment_id": finding.comment_id,
            "original_text": self._cipher.encrypt(suggestion.original_text),
            "proposed_change": self._cipher.encrypt(suggestion.proposed_change),
            "reason_de": self._cipher.encrypt(suggestion.reason_de),
            "category": finding.finding.category.value,
            "priority": finding.finding.priority.value,
            "status": finding.status.value,
            "created_at": finding.created_at,
            "updated_at": finding.updated_at,
        }

    def to_domain(self, row: FindingRow) -> StoredFinding:
        return StoredFinding(
            key=row.key,
            doc_id=row.doc_id,
            run_id=row.run_id,
            comment_id=row.comment_id,
            finding=Finding(
                suggestion=Suggestion(
                    original_text=self._cipher.decrypt(row.original_text),
                    proposed_change=self._cipher.decrypt(row.proposed_change),
                    reason_de=self._cipher.decrypt(row.reason_de),
                ),
                category=Category(row.category),
                priority=Priority(row.priority),
            ),
            status=FindingStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
