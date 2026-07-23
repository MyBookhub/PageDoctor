from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from pagedoctor.adapters.google.docs_source import GoogleDocsSource
from pagedoctor.domain.errors import DocumentAccessDeniedError

if TYPE_CHECKING:
    from googleapiclient._apis.docs.v1 import DocsResource


def _document() -> dict[str, Any]:
    return {
        "body": {
            "content": [
                {
                    "startIndex": 1,
                    "paragraph": {
                        "elements": [
                            {"startIndex": 1, "textRun": {"content": "Hallo Welt.\n"}},
                        ]
                    },
                },
                {
                    "startIndex": 13,
                    "paragraph": {
                        "elements": [
                            {"startIndex": 13, "textRun": {"content": "Gut "}},
                            {"startIndex": 17, "textRun": {"content": "so\n"}},
                            {"startIndex": 20, "horizontalRule": {}},
                        ]
                    },
                },
                {
                    "startIndex": 21,
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "startIndex": 24,
                                                            "textRun": {"content": "Zelle.\n"},
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                },
            ]
        }
    }


def _service(document: dict[str, Any]) -> MagicMock:
    client = MagicMock()
    client.documents.return_value.get.return_value.execute.return_value = document
    return client


def _source(client: MagicMock) -> GoogleDocsSource:
    return GoogleDocsSource(cast("DocsResource", client))


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def test_read_extracts_plain_text() -> None:
    source = _source(_service(_document()))

    document = source.read("doc-1")

    assert document.doc_id == "doc-1"
    assert document.text == "Hallo Welt.\nGut so\nZelle.\n"


def test_read_builds_index_map_mapping_runs_to_docs_indices() -> None:
    source = _source(_service(_document()))

    index_map = source.read("doc-1").index_map

    assert index_map.plain_text_length == 26
    spans = [(s.text_start, s.text_end, s.doc_start_index) for s in index_map.segments]
    assert spans == [
        (0, 12, 1),
        (12, 16, 13),
        (16, 19, 17),
        (19, 26, 24),
    ]


def test_read_requests_the_target_doc_with_all_tabs() -> None:
    client = _service(_document())

    _source(client).read("doc-1")

    client.documents.return_value.get.assert_called_once_with(
        documentId="doc-1", includeTabsContent=True
    )


def _paragraph(text: str, start_index: int = 1) -> dict[str, Any]:
    return {"paragraph": {"elements": [{"startIndex": start_index, "textRun": {"content": text}}]}}


def _tab(text: str, children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "documentTab": {"body": {"content": [_paragraph(text)]}},
        "childTabs": children or [],
    }


def test_read_concatenates_all_tabs_in_display_order() -> None:
    # A tabbed book: without includeTabsContent the API serves only the first tab —
    # the review must see every chapter.
    document = {
        "tabs": [
            _tab("Kapitel eins.\n"),
            _tab("Kapitel zwei.\n", children=[_tab("Unterkapitel zwei-a.\n")]),
            _tab("Kapitel drei.\n"),
        ]
    }

    result = _source(_service(document)).read("doc-1")

    assert result.text == "Kapitel eins.\nKapitel zwei.\nUnterkapitel zwei-a.\nKapitel drei.\n"
    assert result.index_map.plain_text_length == len(result.text)


def test_tabbed_document_wins_over_legacy_body() -> None:
    document = {
        "body": {"content": [_paragraph("Nur der erste Tab.\n")]},
        "tabs": [_tab("Tab eins.\n"), _tab("Tab zwei.\n")],
    }

    result = _source(_service(document)).read("doc-1")

    assert result.text == "Tab eins.\nTab zwei.\n"


def test_empty_document_yields_empty_text() -> None:
    source = _source(_service({}))

    document = source.read("doc-1")

    assert document.text == ""
    assert document.index_map.segments == ()


def test_permission_denied_maps_to_domain_error() -> None:
    client = MagicMock()
    client.documents.return_value.get.return_value.execute.side_effect = _http_error(403)

    with pytest.raises(DocumentAccessDeniedError):
        _source(client).read("doc-1")


def test_not_found_maps_to_domain_error() -> None:
    client = MagicMock()
    client.documents.return_value.get.return_value.execute.side_effect = _http_error(404)

    with pytest.raises(DocumentAccessDeniedError):
        _source(client).read("doc-1")


def test_unexpected_http_error_propagates() -> None:
    client = MagicMock()
    client.documents.return_value.get.return_value.execute.side_effect = _http_error(500)

    with pytest.raises(HttpError):
        _source(client).read("doc-1")
