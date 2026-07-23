from collections.abc import Sequence
from typing import Literal

import anthropic

from pagedoctor.domain.errors import LlmResponseInvalidError, TokenBudgetExceededError
from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.document import TextChunk
from pagedoctor.domain.models.finding import ChunkFindings, Finding
from pagedoctor.domain.prompts.builder import build_prompt_bundle, build_user_message

Effort = Literal["low", "medium", "high", "max"]

_MAX_OUTPUT_TOKENS = 8000


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
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=_MAX_OUTPUT_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": bundle.joined(),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                # Recent-annotations context is volatile, so it rides in the user message —
                # strictly after the cache breakpoint; the system prefix stays byte-stable.
                messages=[
                    {"role": "user", "content": build_user_message(chunk.text, recent_findings)}
                ],
                thinking={"type": "adaptive"},
                output_config={"effort": self._effort},
                output_format=ChunkFindings,
            )
        except anthropic.AnthropicError as error:
            raise LlmResponseInvalidError(str(error)) from error

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
