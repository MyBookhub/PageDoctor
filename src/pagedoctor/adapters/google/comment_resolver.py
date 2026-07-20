from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from pagedoctor.domain.errors import CommentPostingError, DocumentAccessDeniedError

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource


class DriveCommentResolver:
    def __init__(self, drive_service: DriveResource) -> None:
        self._drive = drive_service

    def resolve_comment(self, doc_id: str, comment_id: str) -> None:
        # A Drive comment's `resolved` flag is output-only; resolving is done by a reply.
        try:
            self._drive.replies().create(
                fileId=doc_id, commentId=comment_id, body={"action": "resolve"}, fields="id"
            ).execute()
        except HttpError as error:
            if error.status_code in (403, 404):
                raise DocumentAccessDeniedError(doc_id) from error
            raise CommentPostingError(doc_id) from error
