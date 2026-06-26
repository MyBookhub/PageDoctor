import hashlib
from collections.abc import Sequence

from pagedoctor.domain.models.document import TextChunk


def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_hashes(chunks: Sequence[TextChunk]) -> frozenset[str]:
    return frozenset(chunk_hash(chunk.text) for chunk in chunks)


def changed_chunks(stored_hashes: frozenset[str], chunks: Sequence[TextChunk]) -> list[TextChunk]:
    return [chunk for chunk in chunks if chunk_hash(chunk.text) not in stored_hashes]
