from uuid import uuid4

from fastapi.testclient import TestClient

from fakes.comment_resolver import FakeCommentResolver
from fakes.comments_source import FakeCommentsSource
from fakes.web import DOC_ID, FakeWeb, build_fake_web, fake_settings
from pagedoctor.app.main import create_app
from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.services.comment_format import format_comment_body
from pagedoctor.domain.services.idempotency import finding_key

OTHER_DOC_ID = "other-doc-id"


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
        custom_dictionary=CustomDictionary(),
    )


def _run(doc_id: str = DOC_ID, status: RunStatus = RunStatus.DONE) -> ReviewRun:
    return ReviewRun(
        id=uuid4(),
        doc_id=doc_id,
        config=_config(),
        status=status,
        correlation_id="abc",
        finding_count=2,
    )


def _finding() -> Finding:
    return Finding(
        suggestion=Suggestion(
            original_text="Der Hund schläft.",
            proposed_change="Der Hund schläft tief.",
            reason_de="Präzisere Formulierung.",
        ),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def _client(
    resolver: FakeCommentResolver | None = None, source: FakeCommentsSource | None = None
) -> tuple[TestClient, FakeWeb]:
    web = build_fake_web(
        settings=fake_settings(), comment_resolver=resolver, comments_source=source
    )
    return TestClient(create_app(web.container)), web


def test_state_with_no_prior_run() -> None:
    client, _ = _client()

    with client:
        response = client.get(f"/docs/{DOC_ID}/state")

    assert response.status_code == 200
    assert response.json() == {
        "doc_id": DOC_ID,
        "latest_run_id": None,
        "latest_status": None,
        "latest_finding_count": 0,
    }


def test_review_requires_a_prior_run() -> None:
    client, _ = _client()

    with client:
        response = client.post(f"/docs/{DOC_ID}/review")

    assert response.status_code == 409


def test_review_reuses_latest_config_and_state_reflects_it() -> None:
    client, web = _client()
    web.repository.save(_run())

    with client:
        review_response = client.post(f"/docs/{DOC_ID}/review")
        assert review_response.status_code == 200
        run_id = review_response.json()["run_id"]

        status_response = client.get(f"/docs/{DOC_ID}/runs/{run_id}/status")
        state_response = client.get(f"/docs/{DOC_ID}/state")

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "done"
    assert state_response.json()["latest_run_id"] == run_id


def test_run_status_for_wrong_doc_is_not_found() -> None:
    client, web = _client()
    run = _run()
    web.repository.save(run)

    with client:
        response = client.get(f"/docs/{OTHER_DOC_ID}/runs/{run.id}/status")

    assert response.status_code == 404


def test_resolve_finding_calls_the_resolver_and_drops_out_of_findings() -> None:
    finding = _finding()
    key = finding_key(DOC_ID, finding)
    comment = DocComment(content=format_comment_body(finding, key), resolved=False, id="comment-1")
    source = FakeCommentsSource({DOC_ID: [comment]})
    resolver = FakeCommentResolver()
    client, _ = _client(resolver=resolver, source=source)

    with client:
        response = client.post(f"/docs/{DOC_ID}/findings/{key}/resolve")

    assert response.status_code == 200
    assert response.json() == {"key": key, "resolved": True}
    assert resolver.resolved == [(DOC_ID, "comment-1")]


def test_resolve_unknown_key_is_not_found() -> None:
    source = FakeCommentsSource({DOC_ID: []})
    client, _ = _client(source=source)

    with client:
        response = client.post(f"/docs/{DOC_ID}/findings/deadbeef00000000/resolve")

    assert response.status_code == 404
