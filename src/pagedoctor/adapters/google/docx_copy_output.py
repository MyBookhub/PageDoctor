from __future__ import annotations

import io
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from pagedoctor.adapters.docx.annotator import annotate_docx
from pagedoctor.domain.errors import (
    DocumentAccessDeniedError,
    OutputCopyError,
    PageDoctorError,
)
from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import OutputResult, ReviewRun
from pagedoctor.logging import get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3 import DriveResource

logger = get_logger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

RUN_PROPERTY = "pagedoctor_run"
COPY_SUFFIX = "_lektoriert_v"
_COPY_SUFFIX_RE = re.compile(r"_lektoriert_v\d+$")


class DocxCopyOutputAdapter:
    # Writes findings as natively anchored comments by exporting the source doc to DOCX,
    # injecting OOXML comments, and importing the result as a fresh versioned copy in the
    # configured Lektorat folder (issue #31). The source document is never touched — no
    # batchUpdate, no comments on it, nothing.

    def __init__(self, drive_service: DriveResource, folder_id: str) -> None:
        self._drive = drive_service
        self._folder_id = folder_id

    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> OutputResult:
        # One atomic files.create at the end makes per-finding checkpoints unnecessary.
        # Idempotency (§10) is layered: the durable checkpoint the orchestrator persisted
        # (run.output_doc_id) is consulted first; the Drive lookup by the run id stamped
        # into the copy's appProperties is only the reconciliation net for the crash window
        # between files.create and the checkpoint save — Drive's search index is eventually
        # consistent, so it must never be the sole guard.
        # The consistency report stays unposted for now (issue #29).
        if run.output_doc_id is not None:
            return OutputResult(output_doc_id=run.output_doc_id)
        existing = self.find_copy_for_run(run)
        if existing is not None:
            return OutputResult(output_doc_id=existing)
        content = self.export_docx(run.doc_id)
        annotated = annotate_docx(content, findings)
        name = self.next_copy_name(self.source_name(run.doc_id))
        copy_id = self.create_copy(run, name, annotated)
        logger.info(
            "created lektorat copy",
            extra={"run_id": str(run.id), "finding_count": len(findings)},
        )
        return OutputResult(output_doc_id=copy_id)

    def find_copy_for_run(self, run: ReviewRun) -> str | None:
        # Scoped to the Lektorat folder (§9 minimal scope): the run-id filter alone would be
        # a Drive-wide enumeration over everything ever shared with Sophie.
        query = (
            f"'{self._folder_id}' in parents"
            f" and appProperties has {{ key='{RUN_PROPERTY}' and value='{run.id}' }}"
            " and trashed=false"
        )
        try:
            response = (
                self._drive.files()
                .list(
                    q=query,
                    fields="files(id)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
        except HttpError as error:
            raise self.map_drive_error(run.doc_id, error) from error
        files = response.get("files", [])
        if not files:
            return None
        return files[0]["id"]

    def export_docx(self, doc_id: str) -> bytes:
        try:
            content = self._drive.files().export(fileId=doc_id, mimeType=DOCX_MIME).execute()
        except HttpError as error:
            raise self.map_drive_error(doc_id, error) from error
        # Any: the generated Drive stubs type export().execute() as Any; it is raw bytes.
        return cast("bytes", content)

    def source_name(self, doc_id: str) -> str:
        # supportsAllDrives on every files.* call: BookHub manuscripts live in a Workspace
        # Shared Drive, where the API answers 404 to flag-less requests even with access.
        try:
            metadata = (
                self._drive.files()
                .get(fileId=doc_id, fields="name", supportsAllDrives=True)
                .execute()
            )
        except HttpError as error:
            raise self.map_drive_error(doc_id, error) from error
        return metadata["name"]

    def next_copy_name(self, source_name: str) -> str:
        # A second pass runs on the previous copy, so strip an existing version suffix
        # before appending the next one ("X_lektoriert_v1" -> "X_lektoriert_v2", not
        # "X_lektoriert_v1_lektoriert_v2").
        base = _COPY_SUFFIX_RE.sub("", source_name)
        version = self.highest_existing_version(base) + 1
        return f"{base}{COPY_SUFFIX}{version}"

    def highest_existing_version(self, base: str) -> int:
        name_re = re.compile(rf"^{re.escape(base)}{re.escape(COPY_SUFFIX)}(\d+)$")
        highest = 0
        page_token: str | None = None
        query = f"'{self._folder_id}' in parents and trashed=false"
        fields = "files(name),nextPageToken"
        try:
            while True:
                if page_token is None:
                    request = self._drive.files().list(
                        q=query,
                        fields=fields,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                else:
                    request = self._drive.files().list(
                        q=query,
                        fields=fields,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                response = request.execute()
                for file in response.get("files", []):
                    match = name_re.match(file.get("name", ""))
                    if match is not None:
                        highest = max(highest, int(match.group(1)))
                page_token = response.get("nextPageToken")
                if not page_token:
                    return highest
        except HttpError as error:
            raise OutputCopyError(self._folder_id) from error

    def create_copy(self, run: ReviewRun, name: str, content: bytes) -> str:
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=DOCX_MIME, resumable=False)
        try:
            created = (
                self._drive.files()
                .create(
                    body={
                        "name": name,
                        "mimeType": GOOGLE_DOC_MIME,
                        "parents": [self._folder_id],
                        "appProperties": {RUN_PROPERTY: str(run.id)},
                    },
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except HttpError as error:
            raise self.map_drive_error(run.doc_id, error) from error
        return created["id"]

    def map_drive_error(self, doc_id: str, error: HttpError) -> PageDoctorError:
        if error.status_code in (403, 404):
            return DocumentAccessDeniedError(doc_id)
        return OutputCopyError(doc_id)
