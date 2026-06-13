from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.document import IndexMap, IndexSegment, SourceDocument
from pagedoctor.logging import get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.docs.v1 import DocsResource
    from googleapiclient._apis.docs.v1.schemas import StructuralElement

logger = get_logger(__name__)


class GoogleDocsSource:
    def __init__(self, docs_service: DocsResource) -> None:
        self._docs = docs_service

    def read(self, doc_id: str) -> SourceDocument:
        # Re-read fresh every run: indices shift if the creator edits between passes (§8).
        try:
            document = self._docs.documents().get(documentId=doc_id).execute()
        except HttpError as error:
            if error.status_code in (403, 404):
                raise DocumentAccessDeniedError(doc_id) from error
            raise

        body = document.get("body")
        content = body.get("content", []) if body is not None else []

        parts: list[str] = []
        segments: list[IndexSegment] = []
        collect_text(content, parts, segments, 0)
        text = "".join(parts)

        logger.info("read document source", extra={"segment_count": len(segments)})
        return SourceDocument(
            doc_id=doc_id,
            text=text,
            index_map=IndexMap(plain_text_length=len(text), segments=tuple(segments)),
        )


def collect_text(
    content: list[StructuralElement],
    parts: list[str],
    segments: list[IndexSegment],
    offset: int,
) -> int:
    # Walks paragraphs and table cells, building plain text and a plain-text -> Docs-API
    # index map (one segment per text run) so a future native adapter can resolve spans.
    for element in content:
        paragraph = element.get("paragraph")
        if paragraph is not None:
            for run_element in paragraph.get("elements", []):
                text_run = run_element.get("textRun")
                start_index = run_element.get("startIndex")
                if text_run is None or start_index is None:
                    continue
                run_text = text_run.get("content")
                if not run_text:
                    continue
                parts.append(run_text)
                segments.append(
                    IndexSegment(
                        text_start=offset,
                        text_end=offset + len(run_text),
                        doc_start_index=start_index,
                    )
                )
                offset += len(run_text)
            continue
        table = element.get("table")
        if table is not None:
            for row in table.get("tableRows", []):
                for cell in row.get("tableCells", []):
                    offset = collect_text(cell.get("content", []), parts, segments, offset)
    return offset
