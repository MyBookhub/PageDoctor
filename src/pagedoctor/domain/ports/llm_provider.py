from typing import Protocol

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings


class LlmProviderPort(Protocol):
    # Sync for now; revisit async per-adapter in #3 when the real client lands.
    # Raises LlmResponseInvalidError on unparseable output, TokenBudgetExceededError
    # when a run's token budget is exhausted.
    def analyze(self, chunk: TextChunk, config: ReviewConfig) -> ChunkFindings: ...
