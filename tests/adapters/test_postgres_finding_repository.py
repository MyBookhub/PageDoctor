import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from pagedoctor.adapters.persistence.crypto import FindingCipher
from pagedoctor.adapters.persistence.finding_repository import PostgresFindingRepository
from pagedoctor.config import load_settings
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAGEDOCTOR_LIVE_DB"),
    reason="set PAGEDOCTOR_LIVE_DB=1 to run the Postgres round-trip tests (needs the db container)",
)

NOW = datetime(2026, 7, 9, tzinfo=UTC)


@pytest.fixture
def repository() -> Iterator[PostgresFindingRepository]:
    settings = load_settings()
    engine = create_engine(settings.database_url)
    cipher = FindingCipher(settings.finding_encryption_key.get_secret_value())
    yield PostgresFindingRepository(sessionmaker(bind=engine), cipher)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM findings WHERE doc_id = 'doc-live'"))


def _stored(
    key: str = "k1",
    comment_id: str | None = "c1",
    status: FindingStatus = FindingStatus.OPEN,
    updated_at: datetime = NOW,
) -> StoredFinding:
    return StoredFinding(
        key=key,
        doc_id="doc-live",
        run_id=uuid.UUID(int=1),
        comment_id=comment_id,
        finding=Finding(
            suggestion=Suggestion(
                original_text="Sie „gieng“ nach Hause.",
                proposed_change="Sie ging nach Hause.",
                reason_de="Alte Schreibweise.",
            ),
            category=Category.PROOFREADING,
            priority=Priority.FEHLER,
        ),
        status=status,
        created_at=NOW,
        updated_at=updated_at,
    )


def test_save_then_read_round_trips_through_encryption(
    repository: PostgresFindingRepository,
) -> None:
    stored = _stored()
    repository.save_findings([stored])

    assert repository.open_findings("doc-live") == [stored]


def test_finding_text_is_encrypted_at_rest(repository: PostgresFindingRepository) -> None:
    repository.save_findings([_stored()])

    engine = create_engine(load_settings().database_url)
    with engine.begin() as conn:
        raw = conn.execute(
            text("SELECT original_text FROM findings WHERE doc_id = 'doc-live'")
        ).scalar_one()

    assert "gieng" not in raw


def test_save_is_idempotent_and_preserves_status(repository: PostgresFindingRepository) -> None:
    repository.save_findings([_stored()])
    repository.set_status("doc-live", "c1", FindingStatus.APPLIED)

    repository.save_findings([_stored()])

    assert repository.open_findings("doc-live") == []


def test_purge_expired_removes_old_findings(repository: PostgresFindingRepository) -> None:
    repository.save_findings(
        [
            _stored("old", updated_at=NOW - timedelta(days=100)),
            _stored("fresh", comment_id="c2", updated_at=NOW),
        ]
    )

    removed = repository.purge_expired(cutoff=NOW - timedelta(days=30))

    assert removed == 1
    assert [finding.key for finding in repository.open_findings("doc-live")] == ["fresh"]
