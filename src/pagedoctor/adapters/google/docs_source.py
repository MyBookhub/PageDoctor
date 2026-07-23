from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.document import IndexMap, IndexSegment, SourceDocument
from pagedoctor.logging import get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.docs.v1 import DocsResource
    from googleapiclient._apis.docs.v1.schemas import StructuralElement, Tab

logger = get_logger(__name__)


class GoogleDocsSource:
    def __init__(self, docs_service: DocsResource) -> None:
        self._docs = docs_service

    def read(self, doc_id: str) -> SourceDocument:
        # includeTabsContent: without it the API silently serves only the FIRST tab of a
        # tabbed document — a whole book in tabs would be 97% invisible to the review.
        try:
            document = (
                self._docs.documents().get(documentId=doc_id, includeTabsContent=True).execute()
            )
        except HttpError as error:
            if error.status_code in (403, 404):
                raise DocumentAccessDeniedError(doc_id) from error
            raise

        parts: list[str] = []
        segments: list[IndexSegment] = []
        tabs = document.get("tabs", [])
        if tabs:
            collect_tabs(tabs, parts, segments, 0)
        else:
            body = document.get("body")
            content = body.get("content", []) if body is not None else []
            collect_text(content, parts, segments, 0)
        text = "".join(parts)

        logger.info(
            "read document source",
            extra={"segment_count": len(segments), "tab_count": len(tabs)},
        )
        return SourceDocument(
            doc_id=doc_id,
            text=text,
            index_map=IndexMap(plain_text_length=len(text), segments=tuple(segments)),
        )


def collect_tabs(
    tabs: list[Tab],
    parts: list[str],
    segments: list[IndexSegment],
    offset: int,
) -> int:
    # Depth-first in display order, child tabs after their parent. Doc indices are
    # tab-local, so segments from different tabs overlap in doc_start_index — a future
    # native-suggestion adapter needs the tab id alongside the index (issue #31).
    for tab in tabs:
        document_tab = tab.get("documentTab")
        if document_tab is not None:
            body = document_tab.get("body")
            if body is not None:
                offset = collect_text(body.get("content", []), parts, segments, offset)
        offset = collect_tabs(tab.get("childTabs", []), parts, segments, offset)
    return offset


def collect_text(
    content: list[StructuralElement],
    parts: list[str],
    segments: list[IndexSegment],
    offset: int,
) -> int:
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
