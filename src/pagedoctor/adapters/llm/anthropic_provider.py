from collections.abc import Sequence
from typing import Literal

import anthropic
import pydantic

from pagedoctor.domain.errors import LlmResponseInvalidError, TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings, Finding
from pagedoctor.domain.prompts.builder import build_prompt_bundle, build_user_message
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

Effort = Literal["low", "medium", "high", "max"]

_MAX_OUTPUT_TOKENS = 8000
# A single schema-invalid model response killed a whole 40-chunk run (2026-07-23):
# nondeterministic output noise, not a systematic failure — one retry absorbs it.
_ATTEMPTS_PER_CHUNK = 2


class AnthropicLlmProvider:
    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str,
        effort: Effort,
        token_budget: int | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._effort = effort
        self._token_budget = token_budget
        self._tokens_used = 0

    def analyze(
        self, chunk: TextChunk, config: ReviewConfig, recent_findings: Sequence[Finding]
    ) -> ChunkFindings:
        if self._token_budget is not None and self._tokens_used >= self._token_budget:
            raise TokenBudgetExceededError(
                f"token budget {self._token_budget} reached after {self._tokens_used} tokens"
            )
        bundle = build_prompt_bundle(config)
        last_error: Exception | None = None
        for attempt in range(1, _ATTEMPTS_PER_CHUNK + 1):
            try:
                return self.request_findings(bundle.joined(), chunk, recent_findings)
            except (
                anthropic.AnthropicError,
                pydantic.ValidationError,
                LlmResponseInvalidError,
            ) as error:
                # pydantic.ValidationError: the SDK validates the structured output
                # client-side and raises it raw — without this catch a single noisy
                # response would escape as an untyped error and fail the whole run.
                # LlmResponseInvalidError covers the parsed_output-is-None shape of
                # the same noise, so it retries too.
                last_error = error
                logger.warning(
                    "chunk analysis attempt failed",
                    extra={"attempt": attempt, "error_type": type(error).__name__},
                )
        raise LlmResponseInvalidError(str(last_error)) from last_error

    def request_findings(
        self, system_text: str, chunk: TextChunk, recent_findings: Sequence[Finding]
    ) -> ChunkFindings:
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=_MAX_OUTPUT_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            # Recent-annotations context is volatile, so it rides in the user message —
            # strictly after the cache breakpoint; the system prefix stays byte-stable.
            messages=[{"role": "user", "content": build_user_message(chunk.text, recent_findings)}],
            thinking={"type": "adaptive"},
            output_config={"effort": self._effort},
            output_format=ChunkFindings,
        )
        usage = response.usage
        self._tokens_used += (
            usage.input_tokens
            + usage.output_tokens
            + (usage.cache_creation_input_tokens or 0)
            + (usage.cache_read_input_tokens or 0)
        )
        parsed = response.parsed_output
        if parsed is None:
            raise LlmResponseInvalidError("model returned no structured findings")
        return parsed
