from fastapi.testclient import TestClient

from fakes.comments_source import FakeCommentsSource
from fakes.web import DOC_ID as WEB_DOC_ID
from fakes.web import build_fake_web, fake_settings
from pagedoctor.app.main import create_app
from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.comment_format import format_comment_body
from pagedoctor.domain.services.idempotency import finding_key

DOC_ID = "doc-xyz"
TOKEN = "addon-secret-token"


def _finding(
    original: str = "Der Hund schläft.", category: Category = Category.PROOFREADING
) -> Finding:
    return Finding(
        suggestion=Suggestion(
            original_text=original,
            proposed_change="Der Hund schläft tief.",
            reason_de="Präzisere Formulierung.",
        ),
        category=category,
        priority=Priority.FEHLER,
    )


def _comment(finding: Finding, resolved: bool = False, comment_id: str = "c1") -> DocComment:
    return DocComment(
        id=comment_id,
        content=format_comment_body(finding, finding_key(DOC_ID, finding)),
        resolved=resolved,
    )


def _client(source: FakeCommentsSource, *, token: str | None = None) -> TestClient:
    settings = fake_settings(addon_token=token) if token is not None else fake_settings()
    web = build_fake_web(settings=settings, comments_source=source)
    return TestClient(create_app(web.container))


def test_returns_open_findings_as_json() -> None:
    finding = _finding()
    source = FakeCommentsSource(
        {
            DOC_ID: [
                _comment(finding, comment_id="c1"),
                _comment(_finding("Erledigt."), resolved=True, comment_id="c2"),
            ]
        }
    )

    with _client(source) as client:
        response = client.get(f"/docs/{DOC_ID}/findings")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == DOC_ID
    assert body["findings"] == [
        {
            "key": finding_key(DOC_ID, finding),
            "comment_id": "c1",
            "quote": "Der Hund schläft.",
            "proposed_change": "Der Hund schläft tief.",
            "reason_de": "Präzisere Formulierung.",
            "category": "proofreading",
            "priority": "FEHLER",
        }
    ]


def test_token_required_when_configured() -> None:
    source = FakeCommentsSource({DOC_ID: [_comment(_finding())]})

    with _client(source, token=TOKEN) as client:
        missing = client.get(f"/docs/{DOC_ID}/findings")
        wrong = client.get(f"/docs/{DOC_ID}/findings", headers={"Authorization": "Bearer nope"})
        ok = client.get(f"/docs/{DOC_ID}/findings", headers={"Authorization": f"Bearer {TOKEN}"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200


def test_unknown_doc_returns_404() -> None:
    source = FakeCommentsSource({DOC_ID: [_comment(_finding())]})

    with _client(source) as client:
        response = client.get("/docs/unknown-doc/findings")

    assert response.status_code == 404


def test_resolve_finding_resolves_the_comment() -> None:
    web = build_fake_web()

    with TestClient(create_app(web.container)) as client:
        response = client.post(f"/docs/{DOC_ID}/findings/c1/resolve")

    assert response.status_code == 200
    assert response.json() == {"resolved": True}
    assert "c1" in web.output.resolved


def test_trigger_review_starts_a_run_and_status_reports_done() -> None:
    web = build_fake_web()
    body = {"modes": ["proofreading"], "book_type": "cookbook", "strictness": "standard"}

    with TestClient(create_app(web.container)) as client:
        started = client.post(f"/docs/{WEB_DOC_ID}/review", json=body)
        run_id = started.json()["run_id"]
        progress = client.get(f"/docs/{WEB_DOC_ID}/runs/{run_id}/status")

    assert started.status_code == 200
    assert progress.status_code == 200
    assert progress.json()["status"] == "done"
    assert progress.json()["done"] is True


def test_trigger_review_rejects_empty_modes() -> None:
    web = build_fake_web()
    body = {"modes": [], "book_type": "cookbook", "strictness": "standard"}

    with TestClient(create_app(web.container)) as client:
        response = client.post(f"/docs/{WEB_DOC_ID}/review", json=body)

    assert response.status_code == 422


def test_state_is_unreviewed_before_any_review() -> None:
    web = build_fake_web()

    with TestClient(create_app(web.container)) as client:
        response = client.get(f"/docs/{WEB_DOC_ID}/state")

    assert response.status_code == 200
    assert response.json() == {"reviewed": False, "changed": False}


def test_state_reports_reviewed_after_a_review() -> None:
    web = build_fake_web()
    body = {"modes": ["proofreading"], "book_type": "cookbook", "strictness": "standard"}

    with TestClient(create_app(web.container)) as client:
        client.post(f"/docs/{WEB_DOC_ID}/review", json=body)
        response = client.get(f"/docs/{WEB_DOC_ID}/state")

    assert response.status_code == 200
    assert response.json()["reviewed"] is True


def test_status_for_unknown_run_returns_404() -> None:
    web = build_fake_web()

    with TestClient(create_app(web.container)) as client:
        response = client.get(
            f"/docs/{WEB_DOC_ID}/runs/00000000-0000-0000-0000-000000000009/status"
        )

    assert response.status_code == 404
