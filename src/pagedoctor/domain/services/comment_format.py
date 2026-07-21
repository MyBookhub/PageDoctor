import re
from collections.abc import Sequence

from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Suggestion
from pagedoctor.domain.services.idempotency import KEY_LENGTH

CONSISTENCY_HEADER = "Konsistenzbericht"

# No category/priority label, machine-readable id, or signature is embedded anywhere in the
# visible text (Sophie should read like an editor, not a script) — idempotency instead
# re-derives a finding's key from its own quoted content (see idempotency.finding_key), so
# this parser only needs to recover the quote, the proposal, and the reason. Comments already
# posted under earlier layouts (a "Kategorie · Priorität" header and/or a "— Sophie Hoffmann"
# signature, optionally with a trailing hash key) must stay parseable — findings are always
# re-derived live from Drive comments, never persisted, so a layout this parser stops
# recognizing would silently vanish from open findings and could get re-posted as a duplicate.
_FINDING_COMMENT = re.compile(
    r"Original: „(?P<original>.*?)“\n"
    r"Vorschlag: „(?P<proposed>.*?)“\n"
    r"Begründung: (?P<reason>.*?)"
    rf"(?:\n— Sophie Hoffmann(?:  \[#[0-9a-f]{{{KEY_LENGTH}}}\])?)?$",
    re.DOTALL,
)


def format_comment_body(suggestion: Suggestion) -> str:
    return "\n".join(
        (
            f"Original: „{suggestion.original_text}“",
            f"Vorschlag: „{suggestion.proposed_change}“",
            f"Begründung: {suggestion.reason_de}",
        )
    )


def parse_comment_body(content: str) -> Suggestion | None:
    match = _FINDING_COMMENT.search(content)
    if match is None:
        return None
    return Suggestion(
        original_text=match["original"],
        proposed_change=match["proposed"],
        reason_de=match["reason"],
    )


def open_suggestions(comments: Sequence[DocComment]) -> list[Suggestion]:
    suggestions: list[Suggestion] = []
    for comment in comments:
        if comment.resolved:
            continue
        suggestion = parse_comment_body(comment.content)
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions
