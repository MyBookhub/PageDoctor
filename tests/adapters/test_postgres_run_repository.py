import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from pagedoctor.adapters.persistence.run_repository import PostgresRunRepository
from pagedoctor.config import load_settings
from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.doc_state import DocReviewState
from pagedoctor.domain.models.run import ReviewRun, RunStatus

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAGEDOCTOR_LIVE_DB"),
    reason="set PAGEDOCTOR_LIVE_DB=1 to run the Postgres round-trip tests (needs the db container)",
)


@pytest.fixture
def repository() -> Iterator[PostgresRunRepository]:
    engine = create_engine(load_settings().database_url)
    yield PostgresRunRepository(sessionmaker(bind=engine))
    # Leave no residue in the dev database; these tests create throwaway "doc-live" rows.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM review_runs WHERE doc_id = 'doc-live'"))
        conn.execute(text("DELETE FROM doc_review_states WHERE doc_id = 'doc-live'"))


def _run(status: RunStatus = RunStatus.RUNNING, **overrides: object) -> ReviewRun:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "doc_id": "doc-live",
        "config": config,
        "status": status,
        "correlation_id": "cid-live",
    }
    fields.update(overrides)
    return ReviewRun.model_validate(fields)


def test_save_then_get_round_trips(repository: PostgresRunRepository) -> None:
    run = _run(posted_finding_keys=frozenset({"k1", "k2"}), finding_count=2)

    repository.save(run)

    assert repository.get(run.id) == run


def test_save_is_an_upsert_that_advances_the_checkpoint(repository: PostgresRunRepository) -> None:
    run = _run()
    repository.save(run)

    progressed = run.model_copy(
        update={"status": RunStatus.DONE, "posted_finding_keys": frozenset({"k1"})}
    )
    repository.save(progressed)

    stored = repository.get(run.id)
    assert stored.status is RunStatus.DONE
    assert stored.posted_finding_keys == frozenset({"k1"})


def test_get_unknown_run_raises(repository: PostgresRunRepository) -> None:
    with pytest.raises(RunNotFoundError):
        repository.get(uuid.uuid4())


def test_doc_state_round_trips_and_upserts(repository: PostgresRunRepository) -> None:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )
    state = DocReviewState(
        doc_id="doc-live",
        revision_id="rev-1",
        chunk_hashes=frozenset({"h1", "h2"}),
        config=config,
        updated_at=datetime(2026, 6, 26, tzinfo=UTC),
    )

    repository.save_doc_state(state)
    assert repository.get_doc_state("doc-live") == state

    advanced = state.model_copy(
        update={"revision_id": "rev-2", "chunk_hashes": frozenset({"h1", "h3"})}
    )
    repository.save_doc_state(advanced)

    stored = repository.get_doc_state("doc-live")
    assert stored is not None
    assert stored.revision_id == "rev-2"
    assert stored.chunk_hashes == frozenset({"h1", "h3"})


def test_get_doc_state_unknown_returns_none(repository: PostgresRunRepository) -> None:
    assert repository.get_doc_state("doc-live") is None
