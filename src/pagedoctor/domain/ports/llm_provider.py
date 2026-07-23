from collections.abc import Sequence
from typing import Protocol

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings, Finding


class LlmProviderPort(Protocol):
    # recent_findings: Sophie's rolling memory (issue #41) — the engine passes her most
    # recent annotations so consecutive chunks stay consistent and non-redundant.
    def analyze(
        self, chunk: TextChunk, config: ReviewConfig, recent_findings: Sequence[Finding]
    ) -> ChunkFindings: ...
