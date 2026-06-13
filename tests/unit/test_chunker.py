import pytest

from pagedoctor.domain import services
from pagedoctor.domain.errors import ManuscriptTooLargeError
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.document import IndexMap, SourceDocument, TextChunk
from pagedoctor.domain.services.chunker import chunk_document


def _doc(text: str) -> SourceDocument:
    return SourceDocument(doc_id="d", text=text, index_map=IndexMap(plain_text_length=len(text)))


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _assert_contiguous_cover(text: str, chunks: list[TextChunk]) -> None:
    assert "".join(c.text for c in chunks) == text
    cursor = 0
    for position, chunk in enumerate(chunks):
        assert chunk.index == position
        assert chunk.start_offset == cursor
        assert chunk.text == text[chunk.start_offset : chunk.end_offset]
        cursor = chunk.end_offset
    if chunks:
        assert chunks[-1].end_offset == len(text)


def test_short_document_is_one_chunk() -> None:
    text = "Ein kurzer Absatz.\n\nNoch einer."
    chunks = chunk_document(_doc(text), _config())
    assert len(chunks) == 1
    _assert_contiguous_cover(text, chunks)


def test_packs_paragraphs_to_target_and_covers_text() -> None:
    text = "\n\n".join(f"Absatz Nummer {n} mit etwas Text." for n in range(10))
    chunks = chunk_document(_doc(text), _config(), target_chars=40)
    assert len(chunks) > 1
    _assert_contiguous_cover(text, chunks)
    assert all(len(c.text) <= 60 for c in chunks)


def test_oversized_paragraph_splits_on_sentences() -> None:
    text = "Erster Satz hier. Zweiter Satz folgt. Dritter Satz zum Schluss."
    chunks = chunk_document(_doc(text), _config(), target_chars=25)
    assert len(chunks) > 1
    _assert_contiguous_cover(text, chunks)


def test_abbreviation_is_not_a_sentence_boundary() -> None:
    text = "Das ist z. B. lang genug. Es folgt ein zweiter Satz hier."
    chunks = chunk_document(_doc(text), _config(), target_chars=35)
    _assert_contiguous_cover(text, chunks)
    # The abbreviation stays with its sentence; no chunk starts at "B." or "lang".
    assert any("z. B. lang genug" in c.text for c in chunks)


def test_blank_document_yields_no_chunks() -> None:
    assert chunk_document(_doc(""), _config()) == []
    assert chunk_document(_doc("   \n\n  \t "), _config()) == []


def test_document_over_ceiling_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services.chunker, "MAX_DOCUMENT_CHARS", 100)
    with pytest.raises(ManuscriptTooLargeError):
        chunk_document(_doc("x" * 101), _config())
