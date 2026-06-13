from pagedoctor.domain.models.document import LocatedSpan, TextChunk
from pagedoctor.domain.models.finding import ChunkFindings, Finding


def locate_quote(chunk: TextChunk, quote: str, document_text: str) -> LocatedSpan | None:
    # Never trust model offsets: match the verbatim quote. Search the originating
    # chunk first, fall back to the whole document, and resolve only on a unique
    # match. Ambiguous, garbled, or absent quotes return None (surfaced, not dropped).
    if not quote:
        return None
    local = _unique_span(chunk.text, quote)
    if local is not None:
        return LocatedSpan(
            quote=quote,
            start=chunk.start_offset + local[0],
            end=chunk.start_offset + local[1],
        )
    document = _unique_span(document_text, quote)
    if document is not None:
        return LocatedSpan(quote=quote, start=document[0], end=document[1])
    return None


def locate_findings(
    chunk: TextChunk, chunk_findings: ChunkFindings, document_text: str
) -> list[Finding]:
    return [
        item.model_copy(
            update={"located": locate_quote(chunk, item.suggestion.original_text, document_text)}
        )
        for item in chunk_findings.findings
    ]


def _unique_span(haystack: str, needle: str) -> tuple[int, int] | None:
    first = haystack.find(needle)
    if first == -1 or haystack.find(needle, first + 1) != -1:
        return None
    return first, first + len(needle)
