from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from fakes.comments_source import FakeCommentsSource
from fakes.web import DOC_ID as WEB_DOC_ID
from fakes.web import FakeWeb, build_fake_web, fake_settings
from pagedoctor.app.main import create_app
from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding
from pagedoctor.domain.services.comment_format import format_comment_body
from pagedoctor.domain.services.idempotency import finding_key

DOC_ID = "doc-xyz"
TOKEN = "addon-secret-token"
_AT = datetime(2026, 7, 9, tzinfo=UTC)


def _stored(
    finding: Finding,
    comment_id: str,
    doc_id: str = WEB_DOC_ID,
    status: FindingStatus = FindingStatus.OPEN,
) -> StoredFinding:
    return StoredFinding(
        key=finding_key(doc_id, finding),
        doc_id=doc_id,
        run_id=UUID(int=1),
        comment_id=comment_id,
        finding=finding,
        status=status,
        created_at=_AT,
        updated_at=_AT,
    )


def _seeded_web(finding: Finding, comment_id: str = "c1") -> FakeWeb:
    web = build_fake_web()
    web.finding_repository.save_findings([_stored(finding, comment_id)])
    return web


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
    web = _seeded_web(finding, comment_id="c1")

    with TestClient(create_app(web.container)) as client:
        response = client.get(f"/docs/{WEB_DOC_ID}/findings")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == WEB_DOC_ID
    assert body["findings"] == [
        {
            "key": finding_key(WEB_DOC_ID, finding),
            "comment_id": "c1",
            "quote": "Der Hund schläft.",
            "proposed_change": "Der Hund schläft tief.",
            "reason_de": "Präzisere Formulierung.",
            "category": "proofreading",
            "priority": "FEHLER",
        }
    ]


def test_token_required_when_configured() -> None:
    web = build_fake_web(settings=fake_settings(addon_token=TOKEN))

    with TestClient(create_app(web.container)) as client:
        missing = client.get(f"/docs/{WEB_DOC_ID}/findings")
        wrong = client.get(f"/docs/{WEB_DOC_ID}/findings", headers={"Authorization": "Bearer nope"})
        ok = client.get(
            f"/docs/{WEB_DOC_ID}/findings", headers={"Authorization": f"Bearer {TOKEN}"}
        )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200


def test_unreviewed_doc_returns_no_findings() -> None:
    web = build_fake_web()

    with TestClient(create_app(web.container)) as client:
        response = client.get(f"/docs/{WEB_DOC_ID}/findings")

    assert response.status_code == 200
    assert response.json()["findings"] == []


def test_resolve_records_the_outcome_and_resolves_the_comment() -> None:
    finding = _finding()
    web = _seeded_web(finding, comment_id="c1")

    with TestClient(create_app(web.container)) as client:
        response = client.post(f"/docs/{WEB_DOC_ID}/findings/c1/resolve?outcome=applied")

    assert response.status_code == 200
    assert response.json() == {"resolved": True}
    assert "c1" in web.output.resolved
    # The finding is no longer open (its outcome was recorded).
    assert web.finding_repository.open_findings(WEB_DOC_ID) == []


def test_resolve_requires_an_outcome() -> None:
    web = _seeded_web(_finding(), comment_id="c1")

    with TestClient(create_app(web.container)) as client:
        response = client.post(f"/docs/{WEB_DOC_ID}/findings/c1/resolve")

    assert response.status_code == 422


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
    state = response.json()
    assert state["reviewed"] is False
    assert state["changed"] is False
    assert state["last_reviewed"] is None
    assert state["last_config"] is None


def test_state_reports_reviewed_after_a_review() -> None:
    web = build_fake_web()
    body = {
        "modes": ["proofreading"],
        "book_type": "cookbook",
        "strictness": "thorough",
        "recipe_mode": True,
        "custom_dictionary": ["Ragout", "Sous-vide"],
    }

    with TestClient(create_app(web.container)) as client:
        client.post(f"/docs/{WEB_DOC_ID}/review", json=body)
        response = client.get(f"/docs/{WEB_DOC_ID}/state")

    assert response.status_code == 200
    state = response.json()
    assert state["reviewed"] is True
    assert state["last_reviewed"] is not None
    # The stored settings come back so the sidebar can pre-fill the form next time.
    assert state["last_config"] == {
        "modes": ["proofreading"],
        "book_type": "cookbook",
        "strictness": "thorough",
        "recipe_mode": True,
        "custom_dictionary": ["Ragout", "Sous-vide"],
    }


def test_status_for_unknown_run_returns_404() -> None:
    web = build_fake_web()

    with TestClient(create_app(web.container)) as client:
        response = client.get(
            f"/docs/{WEB_DOC_ID}/runs/00000000-0000-0000-0000-000000000009/status"
        )

    assert response.status_code == 404
