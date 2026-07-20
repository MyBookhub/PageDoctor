from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from pagedoctor.domain.errors import (
    CommentPostingError,
    DocumentAccessDeniedError,
    PageDoctorError,
)
from pagedoctor.domain.models.consistency import ConsistencyReport, TermVariant
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import ReviewRun
from pagedoctor.domain.services.comment_format import MARKER, format_comment_body
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key
from pagedoctor.logging import get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

logger = get_logger(__name__)

_LIST_FIELDS = "comments(content),nextPageToken"


class CommentsOutputAdapter:
    def __init__(self, drive_service: DriveResource) -> None:
        self._drive = drive_service

    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> None:
        already = set(run.posted_finding_keys) | self.posted_keys_in_doc(run.doc_id)
        posted = 0
        for finding in findings:
            key = finding_key(run.doc_id, finding)
            if key in already:
                continue
            self.create_comment(run.doc_id, format_comment_body(finding, key))
            already.add(key)
            posted += 1

        report_key = consistency_report_key(run.doc_id)
        if report_key not in already:
            self.create_comment(run.doc_id, consistency_comment_body(report, report_key))
            posted += 1

        logger.info(
            "posted findings to document",
            extra={"posted_count": posted, "finding_count": len(findings)},
        )

    def posted_keys_in_doc(self, doc_id: str) -> set[str]:
        keys: set[str] = set()
        page_token: str | None = None
        comments_api = self._drive.comments()
        try:
            while True:
                if page_token is None:
                    request = comments_api.list(fileId=doc_id, fields=_LIST_FIELDS)
                else:
                    request = comments_api.list(
                        fileId=doc_id, fields=_LIST_FIELDS, pageToken=page_token
                    )
                response = request.execute()
                for comment in response.get("comments", []):
                    content = comment.get("content")
                    if content:
                        keys.update(MARKER.findall(content))
                page_token = response.get("nextPageToken")
                if not page_token:
                    return keys
        except HttpError as error:
            raise self.map_drive_error(doc_id, error) from error

    def create_comment(self, doc_id: str, content: str) -> None:
        try:
            self._drive.comments().create(
                fileId=doc_id, body={"content": content}, fields="id"
            ).execute()
        except HttpError as error:
            raise self.map_drive_error(doc_id, error) from error

    def map_drive_error(self, doc_id: str, error: HttpError) -> PageDoctorError:
        if error.status_code in (403, 404):
            return DocumentAccessDeniedError(doc_id)
        return CommentPostingError(doc_id)


def consistency_comment_body(report: ConsistencyReport, key: str) -> str:
    lines = [f"[Konsistenzbericht · #{key}]", ""]
    if report.term_variants:
        lines.append("Begriffsvarianten:")
        lines.extend(_variant_line(variant) for variant in report.term_variants)
    if report.spelling_variants:
        lines.append("Schreibweisen:")
        lines.extend(_variant_line(variant) for variant in report.spelling_variants)
    if report.repetition_stats:
        lines.append("Wiederholungen:")
        for stat in report.repetition_stats:
            chapter = f" ({stat.chapter})" if stat.chapter else ""
            lines.append(f"• {stat.term}: {stat.count}×{chapter}")
    if len(lines) == 2:
        lines.append("Keine Auffälligkeiten gefunden.")
    lines.extend(("", "— Sophie Hoffmann"))
    return "\n".join(lines)


def _variant_line(variant: TermVariant) -> str:
    others = ", ".join(sorted(variant.variants))
    return f"• {variant.canonical}: {others} ({variant.occurrences}×)"
