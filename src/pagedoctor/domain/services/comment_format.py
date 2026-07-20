import re
from collections.abc import Sequence

from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.idempotency import KEY_LENGTH

_CATEGORY_LABELS = {Category.PROOFREADING: "Korrektorat", Category.EDITING: "Lektorat"}
_LABEL_TO_CATEGORY = {label: category for category, label in _CATEGORY_LABELS.items()}

_PRIORITY_LABELS = {
    Priority.FEHLER: "Fehler",
    Priority.EMPFEHLUNG: "Empfehlung",
    Priority.HINWEIS: "Hinweis",
}
_LABEL_TO_PRIORITY = {label: priority for priority, label in _PRIORITY_LABELS.items()}

CONSISTENCY_HEADER = "Konsistenzbericht"

# No machine-readable id is embedded anywhere in the visible text (Sophie should read like an
# editor, not a script) — idempotency instead re-derives a finding's key from its own quoted
# content (see idempotency.finding_key), so this parser only needs to recover the fields a
# human already sees.
_FINDING_COMMENT = re.compile(
    r"(?P<label>Korrektorat|Lektorat) · (?P<priority_label>Fehler|Empfehlung|Hinweis)\n"
    r"Original: „(?P<original>.*?)“\n"
    r"Vorschlag: „(?P<proposed>.*?)“\n"
    r"Begründung: (?P<reason>.*?)\n"
    r"— Sophie Hoffmann",
    re.DOTALL,
)

# The very first layout ever shipped (category/priority + a trailing hash key in brackets).
# Findings are always re-derived live from Drive comments, never persisted, so comments
# already posted under this layout must stay parseable or they'd silently vanish from open
# findings and could get re-posted as duplicates on the next review.
_KEY_RE = rf"[0-9a-f]{{{KEY_LENGTH}}}"
_FINDING_COMMENT_LEGACY = re.compile(
    r"\[(?P<label>Korrektorat|Lektorat) · (?P<priority>FEHLER|EMPFEHLUNG|HINWEIS)\]\n"
    r"Original: „(?P<original>.*?)“\n"
    r"Vorschlag: „(?P<proposed>.*?)“\n"
    r"Begründung: (?P<reason>.*?)\n"
    rf"— Sophie Hoffmann  \[#{_KEY_RE}\]",
    re.DOTALL,
)


def format_comment_body(finding: Finding) -> str:
    suggestion = finding.suggestion
    category_label = _CATEGORY_LABELS[finding.category]
    priority_label = _PRIORITY_LABELS[finding.priority]
    return "\n".join(
        (
            f"{category_label} · {priority_label}",
            f"Original: „{suggestion.original_text}“",
            f"Vorschlag: „{suggestion.proposed_change}“",
            f"Begründung: {suggestion.reason_de}",
            "— Sophie Hoffmann",
        )
    )


def parse_comment_body(content: str) -> Finding | None:
    match = _FINDING_COMMENT.search(content)
    if match is not None:
        return Finding(
            suggestion=Suggestion(
                original_text=match["original"],
                proposed_change=match["proposed"],
                reason_de=match["reason"],
            ),
            category=_LABEL_TO_CATEGORY[match["label"]],
            priority=_LABEL_TO_PRIORITY[match["priority_label"]],
        )
    legacy_match = _FINDING_COMMENT_LEGACY.search(content)
    if legacy_match is not None:
        return Finding(
            suggestion=Suggestion(
                original_text=legacy_match["original"],
                proposed_change=legacy_match["proposed"],
                reason_de=legacy_match["reason"],
            ),
            category=_LABEL_TO_CATEGORY[legacy_match["label"]],
            priority=Priority(legacy_match["priority"]),
        )
    return None


def findings_from_comments(comments: Sequence[DocComment]) -> list[Finding]:
    findings: list[Finding] = []
    for comment in comments:
        if comment.resolved:
            continue
        finding = parse_comment_body(comment.content)
        if finding is not None:
            findings.append(finding)
    return findings
