from fastapi.testclient import TestClient

from fakes.comments_source import FakeCommentsSource
from fakes.web import build_fake_web, fake_settings
from pagedoctor.app.main import create_app
from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Suggestion
from pagedoctor.domain.services.comment_format import format_comment_body
from pagedoctor.domain.services.idempotency import finding_key

DOC_ID = "doc-xyz"
TOKEN = "addon-secret-token"


def _suggestion(original: str = "Der Hund schläft.") -> Suggestion:
    return Suggestion(
        original_text=original,
        proposed_change="Der Hund schläft tief.",
        reason_de="Präzisere Formulierung.",
    )


def _comment(suggestion: Suggestion, resolved: bool = False) -> DocComment:
    return DocComment(content=format_comment_body(suggestion), resolved=resolved)


def _client(source: FakeCommentsSource, *, token: str | None = None) -> TestClient:
    settings = fake_settings(addon_token=token) if token is not None else fake_settings()
    web = build_fake_web(settings=settings, comments_source=source)
    return TestClient(create_app(web.container))


def test_returns_open_findings_as_json() -> None:
    suggestion = _suggestion()
    source = FakeCommentsSource(
        {DOC_ID: [_comment(suggestion), _comment(_suggestion("Erledigt."), resolved=True)]}
    )

    with _client(source) as client:
        response = client.get(f"/docs/{DOC_ID}/findings")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == DOC_ID
    assert body["findings"] == [
        {
            "key": finding_key(DOC_ID, suggestion),
            "comment_id": None,
            "quote": "Der Hund schläft.",
            "proposed_change": "Der Hund schläft tief.",
            "reason_de": "Präzisere Formulierung.",
        }
    ]


def test_token_required_when_configured() -> None:
    source = FakeCommentsSource({DOC_ID: [_comment(_suggestion())]})

    with _client(source, token=TOKEN) as client:
        missing = client.get(f"/docs/{DOC_ID}/findings")
        wrong = client.get(f"/docs/{DOC_ID}/findings", headers={"Authorization": "Bearer nope"})
        ok = client.get(f"/docs/{DOC_ID}/findings", headers={"Authorization": f"Bearer {TOKEN}"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200


def test_unknown_doc_returns_404() -> None:
    source = FakeCommentsSource({DOC_ID: [_comment(_suggestion())]})

    with _client(source) as client:
        response = client.get("/docs/unknown-doc/findings")

    assert response.status_code == 404
