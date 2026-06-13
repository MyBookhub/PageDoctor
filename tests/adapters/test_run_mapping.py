import uuid
from datetime import UTC, datetime

from pagedoctor.adapters.persistence.run_repository import to_domain, to_row
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.run import ReviewRun, RunStatus


def _run() -> ReviewRun:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING, CheckMode.EDITING}),
        book_type=BookType.COOKBOOK,
        strictness=Strictness.THOROUGH,
        custom_dictionary=CustomDictionary(allowed_terms=frozenset({"Crème", "Sous-vide"})),
        recipe_mode=True,
    )
    return ReviewRun(
        id=uuid.uuid4(),
        doc_id="doc-7",
        config=config,
        status=RunStatus.INCOMPLETE,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
        finding_count=3,
        correlation_id="cid-7",
        posted_finding_keys=frozenset({"aaa", "bbb", "ccc"}),
        token_budget=50000,
    )


def test_row_round_trip_preserves_every_metadata_field() -> None:
    original = _run()

    assert to_domain(to_row(original)) == original


def test_row_carries_only_metadata_not_content() -> None:
    row = to_row(_run())

    columns = {column.name for column in row.__table__.columns}
    assert columns == {
        "id",
        "doc_id",
        "config",
        "status",
        "started_at",
        "finished_at",
        "finding_count",
        "correlation_id",
        "posted_finding_keys",
        "token_budget",
    }
