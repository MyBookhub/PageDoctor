from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from pagedoctor.adapters.google.comments_output import CommentsOutputAdapter
from pagedoctor.domain.errors import CommentPostingError, DocumentAccessDeniedError
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.consistency import ConsistencyReport, RepetitionStat, TermVariant
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.run import ReviewRun, RunStatus
from pagedoctor.domain.services.idempotency import finding_key

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

DOC_ID = "doc-1"


def _run(posted: frozenset[str] = frozenset()) -> ReviewRun:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )
    return ReviewRun(
        id=uuid.UUID(int=1),
        doc_id=DOC_ID,
        config=config,
        status=RunStatus.WRITING,
        correlation_id="cid",
        posted_finding_keys=posted,
    )


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


def _report(empty: bool = False) -> ConsistencyReport:
    if empty:
        return ConsistencyReport(term_variants=[], spelling_variants=[], repetition_stats=[])
    return ConsistencyReport(
        term_variants=[
            TermVariant(canonical="Basilikum", variants=frozenset({"Baslikum"}), occurrences=3)
        ],
        spelling_variants=[],
        repetition_stats=[RepetitionStat(term="lecker", count=4, chapter="Kapitel 3")],
    )


def _service(existing: list[dict[str, Any]] | None = None) -> MagicMock:
    client = MagicMock()
    client.comments.return_value.list.return_value.execute.return_value = {
        "comments": existing or []
    }
    return client


def _adapter(client: MagicMock) -> CommentsOutputAdapter:
    return CommentsOutputAdapter(cast("DriveResource", client))


def _created_bodies(client: MagicMock) -> list[str]:
    return [
        call.kwargs["body"]["content"]
        for call in client.comments.return_value.create.call_args_list
    ]


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def test_posts_one_comment_per_finding_plus_the_report() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [_finding("a"), _finding("b")], _report())

    assert client.comments.return_value.create.call_count == 3


def test_never_edits_the_manuscript() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [_finding()], _report(empty=True))

    assert not any("batchUpdate" in str(call) for call in client.mock_calls)
    assert not any("documents" in str(call) for call in client.mock_calls)


def test_comment_carries_all_required_fields() -> None:
    client = _service()
    finding = _finding()

    _adapter(client).write_findings(_run(), [finding], _report(empty=True))

    body = _created_bodies(client)[0]
    assert "Korrektorat" in body
    assert "Fehler" in body
    assert "Der Hund schläft." in body
    assert "Der Hund schläft tief." in body
    assert "Präzisere Formulierung." in body
    assert "#" not in body
    assert finding_key(DOC_ID, finding) not in body


def test_editing_finding_labelled_lektorat() -> None:
    client = _service()

    _adapter(client).write_findings(
        _run(), [_finding(category=Category.EDITING)], _report(empty=True)
    )

    assert "Lektorat" in _created_bodies(client)[0]


def test_consistency_report_posts_as_single_comment() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [], _report())

    bodies = _created_bodies(client)
    assert len(bodies) == 1
    assert bodies[0].startswith("Konsistenzbericht\n")
    assert "Basilikum" in bodies[0]
    assert "lecker" in bodies[0]


def test_re_posting_the_same_run_creates_no_duplicates() -> None:
    client = _service()
    findings = [_finding("a"), _finding("b")]

    adapter = _adapter(client)
    adapter.write_findings(_run(), findings, _report())

    existing = [{"content": body} for body in _created_bodies(client)]
    client.comments.return_value.list.return_value.execute.return_value = {"comments": existing}
    client.comments.return_value.create.reset_mock()

    adapter.write_findings(_run(), findings, _report())

    assert client.comments.return_value.create.call_count == 0


def test_short_marker_in_existing_comment_is_not_treated_as_a_key() -> None:
    client = _service(existing=[{"content": "Anmerkung [#1] siehe [#abc] oben."}])
    finding = _finding()

    _adapter(client).write_findings(_run(), [finding], _report(empty=True))

    finding_comments = [b for b in _created_bodies(client) if "Konsistenzbericht" not in b]
    assert len(finding_comments) == 1


def test_findings_in_the_run_checkpoint_are_skipped() -> None:
    client = _service()
    finding = _finding()

    _adapter(client).write_findings(
        _run(posted=frozenset({finding_key(DOC_ID, finding)})), [finding], _report(empty=True)
    )

    bodies = _created_bodies(client)
    assert all("Konsistenzbericht" in body for body in bodies)
    assert len(bodies) == 1


def test_duplicate_findings_within_one_call_post_once() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [_finding(), _finding()], _report(empty=True))

    finding_comments = [b for b in _created_bodies(client) if "Konsistenzbericht" not in b]
    assert len(finding_comments) == 1


def test_existing_comments_are_paginated() -> None:
    client = _service()
    client.comments.return_value.list.return_value.execute.side_effect = [
        {"comments": [], "nextPageToken": "page-2"},
        {"comments": []},
    ]

    _adapter(client).write_findings(_run(), [], _report(empty=True))

    assert client.comments.return_value.list.call_count == 2


def test_permission_denied_maps_to_domain_error() -> None:
    client = _service()
    client.comments.return_value.create.return_value.execute.side_effect = _http_error(403)

    with pytest.raises(DocumentAccessDeniedError):
        _adapter(client).write_findings(_run(), [_finding()], _report(empty=True))


def test_unexpected_drive_error_maps_to_comment_posting_error() -> None:
    client = _service()
    client.comments.return_value.create.return_value.execute.side_effect = _http_error(500)

    with pytest.raises(CommentPostingError):
        _adapter(client).write_findings(_run(), [_finding()], _report(empty=True))
