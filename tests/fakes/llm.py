from collections.abc import Sequence

from pagedoctor.domain.errors import TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings, Finding


class FakeLlmProvider:
    def __init__(
        self,
        responses: dict[int, ChunkFindings] | None = None,
        default: ChunkFindings | None = None,
        budget_after: int | None = None,
    ) -> None:
        self._responses = responses or {}
        self._default = default if default is not None else ChunkFindings(findings=[])
        self._budget_after = budget_after
        self.calls: list[TextChunk] = []
        # The rolling-memory window each call received (issue #41), for assertions.
        self.recent_windows: list[tuple[Finding, ...]] = []

    def analyze(
        self, chunk: TextChunk, config: ReviewConfig, recent_findings: Sequence[Finding]
    ) -> ChunkFindings:
        if self._budget_after is not None and len(self.calls) >= self._budget_after:
            raise TokenBudgetExceededError(f"budget exhausted after {self._budget_after} calls")
        self.calls.append(chunk)
        self.recent_windows.append(tuple(recent_findings))
        return self._responses.get(chunk.index, self._default)
