import os

import anthropic
import pytest

from pagedoctor.adapters.llm.anthropic_provider import AnthropicLlmProvider
from pagedoctor.config import load_settings
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings
from pagedoctor.domain.prompts.builder import build_prompt_bundle

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAGEDOCTOR_LIVE_ANTHROPIC"),
    reason="set PAGEDOCTOR_LIVE_ANTHROPIC=1 to run live Anthropic tests",
)


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


@pytest.fixture
def client() -> anthropic.Anthropic:
    settings = load_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def test_stable_prefix_is_cached(client: anthropic.Anthropic) -> None:
    settings = load_settings()
    prefix = build_prompt_bundle(_config()).joined()
    system: list[anthropic.types.TextBlockParam] = [
        {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}
    ]
    client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=128,
        system=system,
        messages=[{"role": "user", "content": "Ein erster kurzer Satz zum Aufwaermen."}],
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        output_format=ChunkFindings,
    )
    second = client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=128,
        system=system,
        messages=[{"role": "user", "content": "Ein zweiter, anderer kurzer Satz."}],
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        output_format=ChunkFindings,
    )
    assert (second.usage.cache_read_input_tokens or 0) > 0


def test_returns_german_findings(client: anthropic.Anthropic) -> None:
    settings = load_settings()
    provider = AnthropicLlmProvider(client, model=settings.anthropic_model, effort="low")
    text = "Das ist ein Rezpet, dass wirklich gut schmeckt."
    chunk = TextChunk(index=0, text=text, start_offset=0, end_offset=len(text))
    result = provider.analyze(chunk, _config(), ())
    assert result.findings
    reasons = " ".join(finding.suggestion.reason_de for finding in result.findings)
    assert reasons.strip()
    assert "KI" not in reasons and "AI" not in reasons
