from typing import cast
from unittest.mock import MagicMock

import anthropic
import pytest

from pagedoctor.adapters.llm.anthropic_provider import AnthropicLlmProvider
from pagedoctor.domain.errors import LlmResponseInvalidError, TokenBudgetExceededError
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


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _chunk() -> TextChunk:
    text = "Der Hund ist braun und die Katze schlaeft."
    return TextChunk(index=0, text=text, start_offset=0, end_offset=len(text))


def _usage(total: int) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = total // 2
    usage.output_tokens = total - total // 2
    usage.cache_creation_input_tokens = 0
    usage.cache_read_input_tokens = 0
    return usage


def _response(parsed: ChunkFindings | None, total: int = 10) -> MagicMock:
    response = MagicMock()
    response.parsed_output = parsed
    response.usage = _usage(total)
    return response


def _findings() -> ChunkFindings:
    return ChunkFindings(
        findings=[
            Finding(
                suggestion=Suggestion(original_text="a", proposed_change="b", reason_de="c"),
                category=Category.PROOFREADING,
                priority=Priority.FEHLER,
            )
        ]
    )


def _provider(client: MagicMock, token_budget: int | None = None) -> AnthropicLlmProvider:
    return AnthropicLlmProvider(
        cast(anthropic.Anthropic, client),
        model="claude-opus-4-8",
        effort="high",
        token_budget=token_budget,
    )


def test_analyze_sends_expected_request_and_returns_parsed() -> None:
    client = MagicMock()
    client.messages.parse.return_value = _response(_findings())
    chunk = _chunk()

    result = _provider(client).analyze(chunk, _config())

    assert result == _findings()
    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["output_format"] is ChunkFindings
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["thinking"] == {"type": "adaptive"}
    assert kwargs["output_config"] == {"effort": "high"}
    system_block = kwargs["system"][0]
    assert system_block["cache_control"] == {"type": "ephemeral"}
    assert chunk.text not in system_block["text"]  # chunk text stays out of the cached prefix
    assert kwargs["messages"][0]["content"] == chunk.text


def test_missing_parsed_output_raises_invalid() -> None:
    client = MagicMock()
    client.messages.parse.return_value = _response(None)
    with pytest.raises(LlmResponseInvalidError):
        _provider(client).analyze(_chunk(), _config())


def test_sdk_error_is_mapped_to_invalid() -> None:
    client = MagicMock()
    client.messages.parse.side_effect = anthropic.AnthropicError("boom")
    with pytest.raises(LlmResponseInvalidError):
        _provider(client).analyze(_chunk(), _config())


def test_budget_trips_after_usage_accumulates() -> None:
    client = MagicMock()
    client.messages.parse.return_value = _response(_findings(), total=100)
    provider = _provider(client, token_budget=100)

    provider.analyze(_chunk(), _config())  # first call consumes 100 tokens
    with pytest.raises(TokenBudgetExceededError):
        provider.analyze(_chunk(), _config())  # pre-check now trips

    assert client.messages.parse.call_count == 1  # no second API call
