from pagedoctor.domain.errors import TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import SourceDocument
from pagedoctor.domain.models.engine import EngineResult
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.ports.llm_provider import LlmProviderPort
from pagedoctor.domain.prompts.builder import RECENT_FINDINGS_IN_PROMPT
from pagedoctor.domain.services.chunker import chunk_document
from pagedoctor.domain.services.consistency import build_consistency_report
from pagedoctor.domain.services.finding_hygiene import clean_findings
from pagedoctor.domain.services.locator import attach_locations


class EditingEngine:
    def __init__(self, provider: LlmProviderPort) -> None:
        self._provider = provider

    def run(self, document: SourceDocument, config: ReviewConfig) -> EngineResult:
        findings: list[Finding] = []
        recent: list[Finding] = []
        complete = True
        for chunk in chunk_document(document, config):
            try:
                chunk_findings = self._provider.analyze(chunk, config, tuple(recent))
            except TokenBudgetExceededError:
                # Expected control flow: a budget trip stops the run with partial results.
                complete = False
                break
            cleaned = clean_findings(attach_locations(chunk, chunk_findings, document.text))
            findings.extend(cleaned)
            # Rolling memory (issue #41): only the hygiene-cleaned findings feed the next
            # chunk's context, capped to the prompt window. Explicit length math — a
            # negative-index del would silently stop capping if the constant were 0.
            recent.extend(cleaned)
            if len(recent) > RECENT_FINDINGS_IN_PROMPT:
                del recent[: len(recent) - RECENT_FINDINGS_IN_PROMPT]
        report = build_consistency_report(document, config)
        return EngineResult(findings=findings, report=report, complete=complete)
