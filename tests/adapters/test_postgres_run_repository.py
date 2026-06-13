import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from pagedoctor.adapters.persistence.run_repository import PostgresRunRepository
from pagedoctor.config import load_settings
from pagedoctor.domain.errors import RunNotFoundError
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.run import ReviewRun, RunStatus

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAGEDOCTOR_LIVE_DB"),
    reason="set PAGEDOCTOR_LIVE_DB=1 to run the Postgres round-trip tests (needs the db container)",
)


@pytest.fixture
def repository() -> Iterator[PostgresRunRepository]:
    engine = create_engine(load_settings().database_url)
    yield PostgresRunRepository(sessionmaker(bind=engine))
    # Leave no residue in the dev database; these tests create throwaway "doc-live" runs.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM review_runs WHERE doc_id = 'doc-live'"))


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
