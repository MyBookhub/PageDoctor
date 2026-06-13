from pagedoctor.domain.errors import TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings


class FakeLlmProvider:
    # Deterministic in-memory LlmProviderPort for engine/domain tests. Returns
    # scripted findings per chunk index, records calls, and can simulate a token
    # budget tripping after a set number of calls.
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

    def analyze(self, chunk: TextChunk, config: ReviewConfig) -> ChunkFindings:
        if self._budget_after is not None and len(self.calls) >= self._budget_after:
            raise TokenBudgetExceededError(f"budget exhausted after {self._budget_after} calls")
        self.calls.append(chunk)
        return self._responses.get(chunk.index, self._default)
