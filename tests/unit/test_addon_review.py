from uuid import UUID, uuid4

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

VALID_PAYLOAD = {
    "modes": ["proofreading", "editing"],
    "book_type": "cookbook",
    "strictness": "standard",
    "recipe_mode": True,
    "custom_dictionary": ["Basilikum", "  ", "Umami"],
}


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
        "changed": False,
        "last_reviewed": None,
        "last_config": None,
    }


def test_review_works_on_a_never_reviewed_doc() -> None:
    # The sidebar always sends its own settings form — no prior run is required.
    client, web = _client()

    with client:
        response = client.post(f"/docs/{DOC_ID}/review", json=VALID_PAYLOAD)

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    saved = web.repository.get(UUID(run_id))
    assert saved.config.book_type.value == "cookbook"
    assert saved.config.recipe_mode is True
    assert saved.config.custom_dictionary.allowed_terms == {"Basilikum", "Umami"}


def test_review_requires_at_least_one_mode() -> None:
    client, _ = _client()
    payload = {**VALID_PAYLOAD, "modes": []}

    with client:
        response = client.post(f"/docs/{DOC_ID}/review", json=payload)

    assert response.status_code == 422


def test_review_rejects_invalid_enum_values() -> None:
    client, _ = _client()
    payload = {**VALID_PAYLOAD, "book_type": "not-a-real-type"}

    with client:
        response = client.post(f"/docs/{DOC_ID}/review", json=payload)

    assert response.status_code == 422


def test_run_status_reports_done_and_state_reflects_it() -> None:
    client, _ = _client()

    with client:
        review_response = client.post(f"/docs/{DOC_ID}/review", json=VALID_PAYLOAD)
        run_id = review_response.json()["run_id"]

        status_response = client.get(f"/docs/{DOC_ID}/runs/{run_id}/status")
        state_response = client.get(f"/docs/{DOC_ID}/state")

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "done"
    assert body["done"] is True
    state_body = state_response.json()
    assert state_body["latest_run_id"] == run_id
    assert state_body["last_config"]["book_type"] == "cookbook"


def test_run_status_for_wrong_doc_is_not_found() -> None:
    client, web = _client()
    run = _run()
    web.repository.save(run)

    with client:
        response = client.get(f"/docs/{OTHER_DOC_ID}/runs/{run.id}/status")

    assert response.status_code == 404


def test_resolve_finding_calls_the_resolver_with_the_outcome_and_drops_out_of_findings() -> None:
    finding = _finding()
    key = finding_key(DOC_ID, finding)
    comment = DocComment(content=format_comment_body(finding, key), resolved=False, id="comment-1")
    source = FakeCommentsSource({DOC_ID: [comment]})
    resolver = FakeCommentResolver()
    client, _ = _client(resolver=resolver, source=source)

    with client:
        response = client.post(
            f"/docs/{DOC_ID}/findings/comment-1/resolve", params={"outcome": "applied"}
        )

    assert response.status_code == 200
    assert response.json() == {"comment_id": "comment-1", "resolved": True}
    assert resolver.resolved == [(DOC_ID, "comment-1")]


def test_resolve_rejects_unknown_outcome() -> None:
    source = FakeCommentsSource({DOC_ID: []})
    client, _ = _client(source=source)

    with client:
        response = client.post(
            f"/docs/{DOC_ID}/findings/comment-1/resolve", params={"outcome": "bogus"}
        )

    assert response.status_code == 422


def test_resolve_unknown_comment_id_is_not_found() -> None:
    source = FakeCommentsSource({DOC_ID: []})
    client, _ = _client(source=source)

    with client:
        response = client.post(
            f"/docs/{DOC_ID}/findings/does-not-exist/resolve", params={"outcome": "dismissed"}
        )

    assert response.status_code == 404
