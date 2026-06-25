import re

from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.idempotency import KEY_LENGTH

_CATEGORY_LABELS = {Category.PROOFREADING: "Korrektorat", Category.EDITING: "Lektorat"}
_LABEL_TO_CATEGORY = {label: category for category, label in _CATEGORY_LABELS.items()}

_KEY_RE = rf"[0-9a-f]{{{KEY_LENGTH}}}"

MARKER = re.compile(rf"\[#({_KEY_RE})\]")

_FINDING_COMMENT = re.compile(
    r"\[(?P<label>Korrektorat|Lektorat) · (?P<priority>FEHLER|EMPFEHLUNG|HINWEIS)\]\n"
    r"Original: „(?P<original>.*?)“\n"
    r"Vorschlag: „(?P<proposed>.*?)“\n"
    r"Begründung: (?P<reason>.*?)\n"
    rf"— Sophie Hoffmann  \[#(?P<key>{_KEY_RE})\]",
    re.DOTALL,
)


def format_comment_body(finding: Finding, key: str) -> str:
    suggestion = finding.suggestion
    label = _CATEGORY_LABELS[finding.category]
    return "\n".join(
        (
            f"[{label} · {finding.priority.value}]",
            f"Original: „{suggestion.original_text}“",
            f"Vorschlag: „{suggestion.proposed_change}“",
            f"Begründung: {suggestion.reason_de}",
            f"— Sophie Hoffmann  [#{key}]",
        )
    )


def parse_comment_body(content: str) -> Finding | None:
    match = _FINDING_COMMENT.search(content)
    if match is None:
        return None
    return Finding(
        suggestion=Suggestion(
            original_text=match["original"],
            proposed_change=match["proposed"],
            reason_de=match["reason"],
        ),
        category=_LABEL_TO_CATEGORY[match["label"]],
        priority=Priority(match["priority"]),
    )
