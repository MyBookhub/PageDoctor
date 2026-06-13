import re

from pagedoctor.domain.errors import ManuscriptTooLargeError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import SourceDocument, TextChunk

TARGET_CHARS = 6000
MAX_DOCUMENT_CHARS = 2_000_000

_ABBREVIATIONS = (
    "z. B.",
    "z.B.",
    "u. a.",
    "u.a.",
    "d. h.",
    "d.h.",
    "bzw.",
    "usw.",
    "ca.",
    "evtl.",
    "ggf.",
    "inkl.",
    "max.",
    "min.",
    "vgl.",
    "Nr.",
    "Abb.",
    "Bd.",
    "S.",
)

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n[ \t\n]*")
_SENTENCE_END = re.compile(r"[.!?:](?=\s)")


def chunk_document(
    document: SourceDocument,
    config: ReviewConfig,
    *,
    target_chars: int = TARGET_CHARS,
) -> list[TextChunk]:
    text = document.text
    if len(text) > MAX_DOCUMENT_CHARS:
        raise ManuscriptTooLargeError(
            f"document has {len(text)} chars, exceeds the {MAX_DOCUMENT_CHARS} limit"
        )
    if not text.strip():
        return []

    units = _split_into_units(text, target_chars)
    chunks: list[TextChunk] = []
    start, end = units[0]
    for unit_start, unit_end in units[1:]:
        if unit_end - start <= target_chars:
            end = unit_end
        else:
            chunks.append(_make_chunk(text, start, end, len(chunks)))
            start, end = unit_start, unit_end
    chunks.append(_make_chunk(text, start, end, len(chunks)))
    return chunks


def _make_chunk(text: str, start: int, end: int, index: int) -> TextChunk:
    return TextChunk(index=index, text=text[start:end], start_offset=start, end_offset=end)


def _split_into_units(text: str, target_chars: int) -> list[tuple[int, int]]:
    bounds = [0, *(m.end() for m in _PARAGRAPH_BREAK.finditer(text)), len(text)]
    ordered = sorted({b for b in bounds if 0 <= b <= len(text)})
    units: list[tuple[int, int]] = []
    for start, end in zip(ordered, ordered[1:], strict=False):
        if end - start <= target_chars:
            units.append((start, end))
        else:
            units.extend(_split_paragraph(text, start, end, target_chars))
    return units


def _split_paragraph(text: str, start: int, end: int, target_chars: int) -> list[tuple[int, int]]:
    local = text[start:end]
    cuts = [0, *_sentence_cuts(local), len(local)]
    ordered = sorted(set(cuts))
    units: list[tuple[int, int]] = []
    for left, right in zip(ordered, ordered[1:], strict=False):
        if right - left <= target_chars:
            units.append((start + left, start + right))
        else:
            units.extend(_hard_split(start + left, start + right, target_chars))
    return units


def _sentence_cuts(paragraph: str) -> list[int]:
    cuts: list[int] = []
    for match in _SENTENCE_END.finditer(paragraph):
        after_punctuation = match.end()
        if not _is_sentence_boundary(paragraph[:after_punctuation]):
            continue
        trailing = re.match(r"\s+", paragraph[after_punctuation:])
        cuts.append(after_punctuation + (trailing.end() if trailing else 0))
    return cuts


_TRAILING_TOKEN = re.compile(r"(\S+)$")


def _is_sentence_boundary(prefix: str) -> bool:
    if any(prefix.endswith(abbreviation) for abbreviation in _ABBREVIATIONS):
        return False
    token_match = _TRAILING_TOKEN.search(prefix[:-1])
    token = token_match.group(1) if token_match else ""
    return not (len(token) == 1 and token.isalpha())


def _hard_split(start: int, end: int, target_chars: int) -> list[tuple[int, int]]:
    return [(pos, min(pos + target_chars, end)) for pos in range(start, end, target_chars)]
