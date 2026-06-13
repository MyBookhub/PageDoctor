from pydantic import BaseModel, ConfigDict


class LocatedSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    quote: str
    start: int
    end: int


class IndexSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    text_start: int
    text_end: int
    doc_start_index: int


class IndexMap(BaseModel):
    # Minimal plain-text <-> Docs-API index mapping. Refined in #4 (Google Docs
    # adapter), where the real documents.get structure defines paragraph/tab indices.
    model_config = ConfigDict(frozen=True)

    plain_text_length: int
    segments: tuple[IndexSegment, ...] = ()


class SourceDocument(BaseModel):
    # In-memory only for the duration of a run; never persisted. Indices are not
    # stable across runs, so the document is re-read fresh on every run.
    model_config = ConfigDict(frozen=True)

    doc_id: str
    text: str
    index_map: IndexMap


class TextChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    text: str
    start_offset: int
    end_offset: int
