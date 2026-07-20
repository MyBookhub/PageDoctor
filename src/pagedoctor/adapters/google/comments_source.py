from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.comment import DocComment
from pagedoctor.logging import get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

logger = get_logger(__name__)

_LIST_FIELDS = "comments(id,content,resolved),nextPageToken"


class GoogleCommentsSource:
    def __init__(self, drive_service: DriveResource) -> None:
        self._drive = drive_service

    def read_comments(self, doc_id: str) -> list[DocComment]:
        comments: list[DocComment] = []
        page_token: str | None = None
        comments_api = self._drive.comments()
        while True:
            try:
                if page_token is None:
                    response = comments_api.list(fileId=doc_id, fields=_LIST_FIELDS).execute()
                else:
                    response = comments_api.list(
                        fileId=doc_id, fields=_LIST_FIELDS, pageToken=page_token
                    ).execute()
            except HttpError as error:
                if error.status_code in (403, 404):
                    raise DocumentAccessDeniedError(doc_id) from error
                raise
            for comment in response.get("comments", []):
                content = comment.get("content")
                if content:
                    comments.append(
                        DocComment(
                            content=content,
                            resolved=bool(comment.get("resolved", False)),
                            id=comment.get("id"),
                        )
                    )
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        logger.info("read document comments", extra={"comment_count": len(comments)})
        return comments
