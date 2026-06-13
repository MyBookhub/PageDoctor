from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.services.locator import attach_locations, locate_quote

DOC = "Der Basilikum ist frisch. Spaeter kommt noch Basilikum dazu."
#      0         1         2         3         4         5
#      0123456789...


def _chunk(text: str, start: int) -> TextChunk:
    return TextChunk(index=0, text=text, start_offset=start, end_offset=start + len(text))


def _finding(quote: str) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=quote, proposed_change="x", reason_de="y"),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def test_unique_quote_resolves_to_absolute_offsets() -> None:
    chunk = _chunk(DOC, 0)
    span = locate_quote(chunk, "ist frisch", DOC)
    assert span is not None
    assert DOC[span.start : span.end] == "ist frisch"


def test_offsets_are_absolute_when_chunk_is_offset() -> None:
    prefix = "Kapitel 1\n\n"
    full = prefix + DOC
    chunk = _chunk(DOC, len(prefix))
    span = locate_quote(chunk, "ist frisch", full)
    assert span is not None
    assert full[span.start : span.end] == "ist frisch"
    assert span.start == len(prefix) + DOC.index("ist frisch")


def test_quote_with_duplicates_is_unlocatable() -> None:
    chunk = _chunk(DOC, 0)
    assert locate_quote(chunk, "Basilikum", DOC) is None


def test_absent_quote_returns_none() -> None:
    chunk = _chunk(DOC, 0)
    assert locate_quote(chunk, "Petersilie", DOC) is None


def test_empty_quote_returns_none() -> None:
    chunk = _chunk(DOC, 0)
    assert locate_quote(chunk, "", DOC) is None


def test_quote_outside_chunk_resolves_via_document_fallback() -> None:
    chunk = _chunk("Anderer Absatz ohne das Zitat.", 100)
    span = locate_quote(chunk, "ist frisch", DOC)
    assert span is not None
    assert DOC[span.start : span.end] == "ist frisch"


def test_attach_locations_keeps_unlocatable_with_none() -> None:
    chunk = _chunk(DOC, 0)
    findings = ChunkFindings(findings=[_finding("ist frisch"), _finding("Basilikum")])
    located = attach_locations(chunk, findings, DOC)
    assert len(located) == 2
    assert located[0].located is not None
    assert located[1].located is None  # ambiguous, surfaced not dropped
