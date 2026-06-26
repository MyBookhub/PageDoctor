from collections.abc import Sequence

from pagedoctor.domain.errors import TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import SourceDocument, TextChunk
from pagedoctor.domain.models.engine import EngineResult
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.ports.llm_provider import LlmProviderPort
from pagedoctor.domain.services.chunker import chunk_document
from pagedoctor.domain.services.consistency import build_consistency_report
from pagedoctor.domain.services.locator import attach_locations


class EditingEngine:
    def __init__(self, provider: LlmProviderPort) -> None:
        self._provider = provider

    def run(self, document: SourceDocument, config: ReviewConfig) -> EngineResult:
        return self.run_chunks(document, config, chunk_document(document, config))

    def run_chunks(
        self, document: SourceDocument, config: ReviewConfig, chunks: Sequence[TextChunk]
    ) -> EngineResult:
        findings: list[Finding] = []
        complete = True
        for chunk in chunks:
            try:
                chunk_findings = self._provider.analyze(chunk, config)
            except TokenBudgetExceededError:
                # Expected control flow: a budget trip stops the run with partial results.
                complete = False
                break
            findings.extend(attach_locations(chunk, chunk_findings, document.text))
        report = build_consistency_report(document, config)
        return EngineResult(findings=findings, report=report, complete=complete)
