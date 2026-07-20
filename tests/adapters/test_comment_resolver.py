from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from pagedoctor.adapters.google.comment_resolver import DriveCommentResolver
from pagedoctor.domain.errors import CommentPostingError, DocumentAccessDeniedError

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

DOC_ID = "doc-1"


def _resolver(client: MagicMock) -> DriveCommentResolver:
    return DriveCommentResolver(cast("DriveResource", client))


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def test_resolve_posts_a_resolve_reply() -> None:
    client = MagicMock()

    _resolver(client).resolve_comment(DOC_ID, "comment-1")

    kwargs = client.replies.return_value.create.call_args.kwargs
    assert kwargs["fileId"] == DOC_ID
    assert kwargs["commentId"] == "comment-1"
    assert kwargs["body"] == {"action": "resolve"}


def test_permission_denied_maps_to_domain_error() -> None:
    client = MagicMock()
    client.replies.return_value.create.return_value.execute.side_effect = _http_error(403)

    with pytest.raises(DocumentAccessDeniedError):
        _resolver(client).resolve_comment(DOC_ID, "comment-1")


def test_unexpected_error_maps_to_comment_posting_error() -> None:
    client = MagicMock()
    client.replies.return_value.create.return_value.execute.side_effect = _http_error(500)

    with pytest.raises(CommentPostingError):
        _resolver(client).resolve_comment(DOC_ID, "comment-1")
