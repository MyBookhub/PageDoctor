from typing import Protocol

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings


class LlmProviderPort(Protocol):
    def analyze(self, chunk: TextChunk, config: ReviewConfig) -> ChunkFindings: ...
