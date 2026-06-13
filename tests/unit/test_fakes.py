from fakes.llm import FakeLlmProvider
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.ports.llm_provider import LlmProviderPort


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def test_fake_satisfies_port_and_scripts_findings() -> None:
    finding = Finding(
        suggestion=Suggestion(
            original_text="Rezpet", proposed_change="Rezept", reason_de="Tippfehler"
        ),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )
    # The annotation makes mypy verify FakeLlmProvider satisfies the Protocol.
    provider: LlmProviderPort = FakeLlmProvider(responses={0: ChunkFindings(findings=[finding])})
    chunk = TextChunk(index=0, text="Rezpet", start_offset=0, end_offset=6)
    assert provider.analyze(chunk, _config()).findings == [finding]
