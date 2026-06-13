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
    # Provisional; the real plain-text to Docs-API index mapping is built in #4.
    model_config = ConfigDict(frozen=True)

    plain_text_length: int
    segments: tuple[IndexSegment, ...] = ()


class SourceDocument(BaseModel):
    # Never persisted (data protection); re-read each run since offsets are not stable.
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
