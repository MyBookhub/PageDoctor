from __future__ import annotations

import io
import uuid
import zipfile
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import docx
import httplib2
import pytest
from googleapiclient.errors import HttpError

from pagedoctor.adapters.google.docx_copy_output import DocxCopyOutputAdapter
from pagedoctor.domain.errors import DocumentAccessDeniedError, OutputCopyError
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.run import ReviewRun, RunStatus

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

DOC_ID = "doc-1"
FOLDER_ID = "lektorat-folder"
RUN_ID = uuid.UUID(int=7)


def _run(output_doc_id: str | None = None) -> ReviewRun:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )
    return ReviewRun(
        id=RUN_ID,
        doc_id=DOC_ID,
        config=config,
        status=RunStatus.WRITING,
        correlation_id="cid",
        output_doc_id=output_doc_id,
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


def _report() -> ConsistencyReport:
    return ConsistencyReport(term_variants=[], spelling_variants=[], repetition_stats=[])


def _docx(text: str = "Der Hund schläft. Danach wacht er auf.") -> bytes:
    document = docx.Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _service(
    source_name: str = "Mein Kochbuch",
    folder_names: list[str] | None = None,
    copy_for_run: str | None = None,
) -> MagicMock:
    client = MagicMock()
    files_api = client.files.return_value

    def list_side_effect(**kwargs: Any) -> MagicMock:
        request = MagicMock()
        query = kwargs.get("q", "")
        if "appProperties" in query:
            files = [{"id": copy_for_run}] if copy_for_run else []
        else:
            files = [{"name": name} for name in (folder_names or [])]
        request.execute.return_value = {"files": files}
        return request

    files_api.list.side_effect = list_side_effect
    files_api.export.return_value.execute.return_value = _docx()
    files_api.get.return_value.execute.return_value = {"name": source_name}
    files_api.create.return_value.execute.return_value = {"id": "copy-new"}
    return client


def _adapter(client: MagicMock) -> DocxCopyOutputAdapter:
    return DocxCopyOutputAdapter(cast("DriveResource", client), FOLDER_ID)


def _create_kwargs(client: MagicMock) -> dict[str, Any]:
    call = client.files.return_value.create.call_args
    assert call is not None
    return dict(call.kwargs)


def _uploaded_bytes(client: MagicMock) -> bytes:
    media = _create_kwargs(client)["media_body"]
    # Any: MediaIoBaseUpload.getbytes is untyped in the stubs; it returns raw bytes.
    return cast(bytes, media.getbytes(0, media.size()))


def test_creates_versioned_copy_in_the_lektorat_folder() -> None:
    client = _service()

    result = _adapter(client).write_findings(_run(), [_finding()], _report())

    assert result.output_doc_id == "copy-new"
    body = _create_kwargs(client)["body"]
    assert body["name"] == "Mein Kochbuch_lektoriert_v1"
    assert body["parents"] == [FOLDER_ID]
    assert body["mimeType"] == "application/vnd.google-apps.document"
    assert body["appProperties"] == {"pagedoctor_run": str(RUN_ID)}


def test_uploaded_copy_carries_the_anchored_comment() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [_finding()], _report())

    with zipfile.ZipFile(io.BytesIO(_uploaded_bytes(client))) as archive:
        comments = archive.read("word/comments.xml").decode("utf-8")
        document = archive.read("word/document.xml").decode("utf-8")
    assert "Sophie Hoffmann" in comments
    assert "Der Hund schläft tief." in comments
    assert "commentRangeStart" in document


def test_version_increments_past_existing_copies() -> None:
    client = _service(
        folder_names=["Mein Kochbuch_lektoriert_v1", "Mein Kochbuch_lektoriert_v2", "Anderes Buch"]
    )

    _adapter(client).write_findings(_run(), [_finding()], _report())

    assert _create_kwargs(client)["body"]["name"] == "Mein Kochbuch_lektoriert_v3"


def test_second_pass_on_a_copy_strips_the_old_suffix() -> None:
    client = _service(
        source_name="Mein Kochbuch_lektoriert_v1", folder_names=["Mein Kochbuch_lektoriert_v1"]
    )

    _adapter(client).write_findings(_run(), [_finding()], _report())

    assert _create_kwargs(client)["body"]["name"] == "Mein Kochbuch_lektoriert_v2"


def test_retried_run_reuses_its_existing_copy() -> None:
    client = _service(copy_for_run="copy-from-first-attempt")

    result = _adapter(client).write_findings(_run(), [_finding()], _report())

    assert result.output_doc_id == "copy-from-first-attempt"
    assert client.files.return_value.create.call_count == 0
    assert client.files.return_value.export.call_count == 0


def test_checkpointed_run_makes_no_drive_calls_at_all() -> None:
    # §10: the durable checkpoint (run.output_doc_id) wins before any Drive lookup —
    # the eventually-consistent search index is never the sole idempotency guard.
    client = _service()

    result = _adapter(client).write_findings(
        _run(output_doc_id="copy-checkpointed"), [_finding()], _report()
    )

    assert result.output_doc_id == "copy-checkpointed"
    assert client.files.return_value.list.call_count == 0
    assert client.files.return_value.export.call_count == 0
    assert client.files.return_value.create.call_count == 0


def test_run_lookup_is_scoped_to_the_lektorat_folder() -> None:
    # §9 minimal scope: the idempotency lookup must never enumerate Drive-wide.
    client = _service(copy_for_run="copy-x")

    _adapter(client).write_findings(_run(), [], _report())

    query = client.files.return_value.list.call_args_list[0].kwargs["q"]
    assert f"'{FOLDER_ID}' in parents" in query
    assert "appProperties" in query


def test_zero_findings_still_creates_the_copy() -> None:
    client = _service()

    result = _adapter(client).write_findings(_run(), [], _report())

    assert result.output_doc_id == "copy-new"
    assert client.files.return_value.create.call_count == 1


def test_never_touches_the_source_document() -> None:
    client = _service()

    _adapter(client).write_findings(_run(), [_finding()], _report())

    assert not any("batchUpdate" in str(call) for call in client.mock_calls)
    assert not any("comments" in str(call) for call in client.mock_calls)
    assert not any("documents" in str(call) for call in client.mock_calls)


def test_export_permission_denied_maps_to_domain_error() -> None:
    client = _service()
    error = HttpError(httplib2.Response({"status": "403"}), b"{}")
    client.files.return_value.export.return_value.execute.side_effect = error

    with pytest.raises(DocumentAccessDeniedError):
        _adapter(client).write_findings(_run(), [_finding()], _report())


def test_unexpected_drive_error_maps_to_output_copy_error() -> None:
    client = _service()
    error = HttpError(httplib2.Response({"status": "500"}), b"{}")
    client.files.return_value.create.return_value.execute.side_effect = error

    with pytest.raises(OutputCopyError):
        _adapter(client).write_findings(_run(), [_finding()], _report())
