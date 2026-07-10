from datetime import UTC, datetime, timedelta
from uuid import UUID

from fakes.finding_repository import InMemoryFindingRepository
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding

DOC_ID = "doc-1"
RUN_ID = UUID(int=1)
NOW = datetime(2026, 7, 9, tzinfo=UTC)


def _stored(
    key: str = "k1",
    comment_id: str | None = "c1",
    status: FindingStatus = FindingStatus.OPEN,
    updated_at: datetime = NOW,
) -> StoredFinding:
    return StoredFinding(
        key=key,
        doc_id=DOC_ID,
        run_id=RUN_ID,
        comment_id=comment_id,
        finding=Finding(
            suggestion=Suggestion(
                original_text="Der Hund schläft.",
                proposed_change="Der Hund schläft tief.",
                reason_de="Präzisere Formulierung.",
            ),
            category=Category.PROOFREADING,
            priority=Priority.FEHLER,
        ),
        status=status,
        created_at=NOW,
        updated_at=updated_at,
    )


def test_open_findings_returns_only_open() -> None:
    repo = InMemoryFindingRepository()
    repo.save_findings([_stored("k1"), _stored("k2", comment_id="c2")])
    repo.set_status(DOC_ID, "c2", FindingStatus.DISMISSED)

    open_keys = [finding.key for finding in repo.open_findings(DOC_ID)]

    assert open_keys == ["k1"]


def test_save_is_idempotent_and_preserves_status() -> None:
    repo = InMemoryFindingRepository()
    repo.save_findings([_stored("k1")])
    repo.set_status(DOC_ID, "c1", FindingStatus.APPLIED)

    # A re-review re-saves the same finding; its applied status must survive.
    repo.save_findings([_stored("k1")])

    assert repo.open_findings(DOC_ID) == []


def test_purge_expired_removes_only_old_rows() -> None:
    repo = InMemoryFindingRepository()
    repo.save_findings(
        [
            _stored("old", updated_at=NOW - timedelta(days=40)),
            _stored("fresh", comment_id="c2", updated_at=NOW),
        ]
    )

    removed = repo.purge_expired(cutoff=NOW - timedelta(days=30))

    assert removed == 1
    assert [finding.key for finding in repo.open_findings(DOC_ID)] == ["fresh"]
