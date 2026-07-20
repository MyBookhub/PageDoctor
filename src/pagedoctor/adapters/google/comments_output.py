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
from pagedoctor.domain.services.comment_format import (
    CONSISTENCY_HEADER,
    format_comment_body,
    parse_comment_body,
)
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
        # No id is embedded in the posted text (§9 persona voice), so a finding's key is
        # re-derived from its own quoted content when re-scanning the doc — this makes the
        # scan itself the source of truth, not a marker string.
        existing = self.list_comment_contents(run.doc_id)
        already = set(run.posted_finding_keys) | self.posted_finding_keys(run.doc_id, existing)
        posted = 0
        for finding in findings:
            key = finding_key(run.doc_id, finding)
            if key in already:
                continue
            self.create_comment(run.doc_id, format_comment_body(finding))
            already.add(key)
            posted += 1

        report_key = consistency_report_key(run.doc_id)
        consistency_already_posted = report_key in run.posted_finding_keys or any(
            content.strip().startswith(CONSISTENCY_HEADER) for content in existing
        )
        if not consistency_already_posted:
            self.create_comment(run.doc_id, consistency_comment_body(report))
            posted += 1

        logger.info(
            "posted findings to document",
            extra={"posted_count": posted, "finding_count": len(findings)},
        )

    def posted_finding_keys(self, doc_id: str, contents: Sequence[str]) -> set[str]:
        keys: set[str] = set()
        for content in contents:
            finding = parse_comment_body(content)
            if finding is not None:
                keys.add(finding_key(doc_id, finding))
        return keys

    def list_comment_contents(self, doc_id: str) -> list[str]:
        contents: list[str] = []
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
                contents.extend(
                    content
                    for comment in response.get("comments", [])
                    if (content := comment.get("content"))
                )
                page_token = response.get("nextPageToken")
                if not page_token:
                    return contents
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


def consistency_comment_body(report: ConsistencyReport) -> str:
    lines = [CONSISTENCY_HEADER, ""]
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
