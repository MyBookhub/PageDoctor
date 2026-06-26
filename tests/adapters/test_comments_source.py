from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from pagedoctor.adapters.google.comments_source import GoogleCommentsSource
from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.comment import DocComment

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

DOC_ID = "doc-1"


def _service(pages: list[dict[str, Any]]) -> MagicMock:
    client = MagicMock()
    client.comments.return_value.list.return_value.execute.side_effect = pages
    return client


def _source(client: MagicMock) -> GoogleCommentsSource:
    return GoogleCommentsSource(cast("DriveResource", client))


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def test_reads_id_content_and_resolved_flag() -> None:
    client = _service(
        [
            {
                "comments": [
                    {"id": "c1", "content": "offen", "resolved": False},
                    {"id": "c2", "content": "erledigt", "resolved": True},
                ]
            }
        ]
    )

    comments = _source(client).read_comments(DOC_ID)

    assert comments == [
        DocComment(id="c1", content="offen", resolved=False),
        DocComment(id="c2", content="erledigt", resolved=True),
    ]


def test_requests_id_content_and_resolved_fields() -> None:
    client = _service([{"comments": []}])

    _source(client).read_comments(DOC_ID)

    kwargs = client.comments.return_value.list.call_args.kwargs
    assert kwargs["fileId"] == DOC_ID
    assert "id" in kwargs["fields"]
    assert "resolved" in kwargs["fields"]


def test_missing_resolved_defaults_to_false() -> None:
    client = _service([{"comments": [{"id": "c1", "content": "ohne Flag"}]}])

    comments = _source(client).read_comments(DOC_ID)

    assert comments == [DocComment(id="c1", content="ohne Flag", resolved=False)]


def test_comment_without_id_is_skipped() -> None:
    client = _service([{"comments": [{"content": "kein id"}]}])

    assert _source(client).read_comments(DOC_ID) == []


def test_paginates_until_exhausted() -> None:
    client = _service(
        [
            {"comments": [{"id": "a", "content": "a", "resolved": False}], "nextPageToken": "p2"},
            {"comments": [{"id": "b", "content": "b", "resolved": False}]},
        ]
    )

    comments = _source(client).read_comments(DOC_ID)

    assert [c.content for c in comments] == ["a", "b"]
    assert client.comments.return_value.list.call_count == 2


def test_permission_denied_maps_to_domain_error() -> None:
    client = MagicMock()
    client.comments.return_value.list.return_value.execute.side_effect = _http_error(403)

    with pytest.raises(DocumentAccessDeniedError):
        _source(client).read_comments(DOC_ID)
