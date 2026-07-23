from typing import cast
from unittest.mock import MagicMock

import anthropic
import pydantic
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

    result = _provider(client).analyze(chunk, _config(), ())

    assert result == _findings()
    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["output_format"] is ChunkFindings
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["thinking"] == {"type": "adaptive"}
    assert kwargs["output_config"] == {"effort": "high"}
    system_block = kwargs["system"][0]
    assert system_block["cache_control"] == {"type": "ephemeral"}
    assert chunk.text not in system_block["text"]
    assert kwargs["messages"][0]["content"] == chunk.text


def test_recent_findings_ride_in_the_user_message_not_the_cached_prefix() -> None:
    # Rolling memory (issue #41) is volatile per call — it must never enter the cached
    # system prefix, or every call would invalidate the prompt cache (§7).
    client = MagicMock()
    client.messages.parse.return_value = _response(_findings())
    chunk = _chunk()
    recent = _findings().findings

    _provider(client).analyze(chunk, _config(), recent)

    kwargs = client.messages.parse.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert "Deine letzten Anmerkungen" in user_content
    assert chunk.text in user_content
    assert "Deine letzten Anmerkungen" not in kwargs["system"][0]["text"]


def test_missing_parsed_output_raises_invalid() -> None:
    client = MagicMock()
    client.messages.parse.return_value = _response(None)
    with pytest.raises(LlmResponseInvalidError):
        _provider(client).analyze(_chunk(), _config(), ())


def test_sdk_error_is_mapped_to_invalid() -> None:
    client = MagicMock()
    client.messages.parse.side_effect = anthropic.AnthropicError("boom")
    with pytest.raises(LlmResponseInvalidError):
        _provider(client).analyze(_chunk(), _config(), ())


def test_one_invalid_response_is_retried_and_the_run_survives() -> None:
    # A single schema-invalid model response must not kill a whole-book run (issue on
    # the 2026-07-23 run): the provider retries the chunk once.
    client = MagicMock()
    invalid = pydantic.ValidationError.from_exception_data("ChunkFindings", [])
    client.messages.parse.side_effect = [invalid, _response(_findings())]

    result = _provider(client).analyze(_chunk(), _config(), ())

    assert result == _findings()
    assert client.messages.parse.call_count == 2


def test_two_invalid_responses_raise_the_typed_domain_error() -> None:
    client = MagicMock()
    invalid = pydantic.ValidationError.from_exception_data("ChunkFindings", [])
    client.messages.parse.side_effect = [invalid, invalid]

    with pytest.raises(LlmResponseInvalidError):
        _provider(client).analyze(_chunk(), _config(), ())

    assert client.messages.parse.call_count == 2


def test_budget_trips_after_usage_accumulates() -> None:
    client = MagicMock()
    client.messages.parse.return_value = _response(_findings(), total=100)
    provider = _provider(client, token_budget=100)

    provider.analyze(_chunk(), _config(), ())
    with pytest.raises(TokenBudgetExceededError):
        provider.analyze(_chunk(), _config(), ())

    assert client.messages.parse.call_count == 1
