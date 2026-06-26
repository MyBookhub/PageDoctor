from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.services.incremental import (
    changed_chunks,
    chunk_hash,
    chunk_hashes,
)


def _chunk(index: int, text: str) -> TextChunk:
    return TextChunk(index=index, text=text, start_offset=0, end_offset=len(text))


def test_chunk_hash_is_deterministic_and_content_sensitive() -> None:
    assert chunk_hash("Hallo") == chunk_hash("Hallo")
    assert chunk_hash("Hallo") != chunk_hash("Hallo.")


def test_all_chunks_changed_when_nothing_stored() -> None:
    chunks = [_chunk(0, "eins"), _chunk(1, "zwei")]
    assert changed_chunks(frozenset(), chunks) == chunks


def test_no_chunks_changed_when_all_hashes_stored() -> None:
    chunks = [_chunk(0, "eins"), _chunk(1, "zwei")]
    assert changed_chunks(chunk_hashes(chunks), chunks) == []


def test_only_new_or_edited_chunks_returned() -> None:
    original = [_chunk(0, "eins"), _chunk(1, "zwei"), _chunk(2, "drei")]
    stored = chunk_hashes(original)
    current = [_chunk(0, "eins"), _chunk(1, "zwei geändert"), _chunk(2, "drei"), _chunk(3, "vier")]
    changed = changed_chunks(stored, current)
    assert [c.text for c in changed] == ["zwei geändert", "vier"]
