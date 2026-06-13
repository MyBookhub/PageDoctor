import re
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fakes.output import FakeOutputPort
from fakes.web import DOC_ID, DOC_TEXT, build_fake_web, fake_settings
from pagedoctor.app.main import create_app
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.run import ReviewRun, RunStatus

_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


def _csrf(client: TestClient) -> str:
    match = _CSRF.search(client.get("/").text)
    assert match is not None
    return match.group(1)


def _valid_form(token: str, **overrides: str | list[str]) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {
        "doc_url": DOC_ID,
        "book_type": "novel_memoir",
        "strictness": "standard",
        "modes": ["proofreading", "editing"],
        "csrf_token": token,
    }
    data.update(overrides)
    return data


def _run(status: RunStatus) -> ReviewRun:
    return ReviewRun(
        id=uuid.uuid4(),
        doc_id=DOC_ID,
        config=ReviewConfig(
            modes=frozenset({CheckMode.PROOFREADING}),
            book_type=BookType.NOVEL_MEMOIR,
            strictness=Strictness.STANDARD,
        ),
        status=status,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        correlation_id="cid",
    )


def test_submit_starts_run_and_runs_to_completion() -> None:
    web = build_fake_web()
    with TestClient(create_app(web.container)) as client:
        resp = client.post("/review", data=_valid_form(_csrf(client)))

        assert resp.status_code == 200
        assert "progress-" in resp.text
        runs = web.repository.list_recent()
        assert len(runs) == 1
        assert runs[0].status is RunStatus.DONE
        # One finding plus the consistency report posted to the doc.
        assert len(web.output.post_log) == 2


def test_progress_fragment_polls_until_terminal() -> None:
    web = build_fake_web()
    pending = _run(RunStatus.PENDING)
    done = _run(RunStatus.DONE)
    web.repository.save(pending)
    web.repository.save(done)

    with TestClient(create_app(web.container)) as client:
        pending_html = client.get(f"/runs/{pending.id}/progress").text
        done_html = client.get(f"/runs/{done.id}/progress").text

    assert 'hx-trigger="every 2s"' in pending_html
    assert "hx-trigger" not in done_html
    assert "Fertig" in done_html


def test_runs_list_shows_runs_and_resume_drives_to_done() -> None:
    web = build_fake_web()
    failed = _run(RunStatus.FAILED)
    web.repository.save(failed)

    with TestClient(create_app(web.container)) as client:
        listing = client.get("/runs").text
        assert DOC_ID[:18] in listing
        assert "Fortsetzen" in listing

        resp = client.post(f"/runs/{failed.id}/resume", data={"csrf_token": _csrf(client)})

        assert resp.status_code == 200
        # The returned fragment polls again (it is not stuck on the old terminal state)...
        assert 'hx-trigger="every 2s"' in resp.text
        # ...and the background resume drives the run to completion.
        assert web.repository.get(failed.id).status is RunStatus.DONE


def test_in_flight_run_offers_no_resume_button() -> None:
    web = build_fake_web()
    web.repository.save(_run(RunStatus.RUNNING))

    with TestClient(create_app(web.container)) as client:
        listing = client.get("/runs").text

    # Resume is recovery-only; an in-flight run must not let a PM launch a duplicate.
    assert "Fortsetzen" not in listing


def test_invalid_doc_url_shows_inline_error_not_crash() -> None:
    web = build_fake_web()
    with TestClient(create_app(web.container)) as client:
        resp = client.post("/review", data=_valid_form(_csrf(client), doc_url="not a link"))

    assert resp.status_code == 422
    assert "gültige Google-Docs-URL" in resp.text
    assert web.repository.list_recent() == []


def test_missing_modes_shows_inline_error() -> None:
    web = build_fake_web()
    with TestClient(create_app(web.container)) as client:
        form = _valid_form(_csrf(client))
        del form["modes"]
        resp = client.post("/review", data=form)

    assert resp.status_code == 422
    assert "Prüfmodus" in resp.text
    assert web.repository.list_recent() == []


def test_background_failure_marks_run_failed_and_progress_shows_error() -> None:
    web = build_fake_web(output=FakeOutputPort(fail_after=0))
    with TestClient(create_app(web.container)) as client:
        resp = client.post("/review", data=_valid_form(_csrf(client)))
        assert resp.status_code == 200

        run = web.repository.list_recent()[0]
        assert run.status is RunStatus.FAILED
        progress = client.get(f"/runs/{run.id}/progress").text

    assert "Fehlgeschlagen" in progress
    assert "hx-trigger" not in progress


def test_wrong_csrf_token_is_rejected() -> None:
    web = build_fake_web()
    with TestClient(create_app(web.container)) as client:
        _csrf(client)
        resp = client.post("/review", data=_valid_form("wrong-token"))

    assert resp.status_code == 422
    assert "Sicherheitstoken" in resp.text
    assert web.repository.list_recent() == []


def test_basic_auth_required_when_configured() -> None:
    settings = fake_settings(basic_auth_user="pm", basic_auth_password="secret")
    web = build_fake_web(settings=settings)
    with TestClient(create_app(web.container)) as client:
        assert client.get("/").status_code == 401
        assert client.get("/", auth=("pm", "secret")).status_code == 200


def test_pages_never_leak_manuscript_or_finding_text() -> None:
    web = build_fake_web()
    with TestClient(create_app(web.container)) as client:
        client.post("/review", data=_valid_form(_csrf(client)))
        run = web.repository.list_recent()[0]
        runs_html = client.get("/runs").text
        progress = client.get(f"/runs/{run.id}/progress").text

    for rendered in (runs_html, progress):
        assert DOC_TEXT not in rendered
        assert "ist dunkelbraun" not in rendered  # the proposed change
        assert "Präziser." not in rendered  # the finding's German reason
