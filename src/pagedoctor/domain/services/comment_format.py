import re
from collections.abc import Sequence

from pagedoctor.domain.models.comment import DocComment, OpenFinding
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.idempotency import KEY_LENGTH

_CATEGORY_LABELS = {Category.PROOFREADING: "Korrektorat", Category.EDITING: "Lektorat"}
_LABEL_TO_CATEGORY = {label: category for category, label in _CATEGORY_LABELS.items()}

# Displayed in Sophie's voice as title-case German; the enum value stays uppercase for the sidebar.
_PRIORITY_LABELS = {
    Priority.FEHLER: "Fehler",
    Priority.EMPFEHLUNG: "Empfehlung",
    Priority.HINWEIS: "Hinweis",
}
_LABEL_TO_PRIORITY = {label: priority for priority, label in _PRIORITY_LABELS.items()}

_KEY_RE = rf"[0-9a-f]{{{KEY_LENGTH}}}"

# The reference marker stays for robust, parse-independent de-duplication (§10: never
# double-post). It is the one machine token in an otherwise natural comment.
MARKER = re.compile(rf"\[#({_KEY_RE})\]")

# Non-greedy fields anchored by the arrow between quotes and the sign-off tail, so a quote
# that itself contains German quotation marks still round-trips.
_FINDING_COMMENT = re.compile(
    r"^(?P<label>Korrektorat|Lektorat) · (?P<priority>Fehler|Empfehlung|Hinweis)\n\n"
    r"„(?P<original>.*?)“\s*→\s*„(?P<proposed>.*?)“\n\n"
    r"(?P<reason>.*?)\n\n"
    rf"– Sophie  \[#(?P<key>{_KEY_RE})\]",
    re.DOTALL,
)


def format_comment_body(finding: Finding, key: str) -> str:
    suggestion = finding.suggestion
    category = _CATEGORY_LABELS[finding.category]
    priority = _PRIORITY_LABELS[finding.priority]
    return "\n".join(
        (
            f"{category} · {priority}",
            "",
            f"„{suggestion.original_text}“ → „{suggestion.proposed_change}“",
            "",
            suggestion.reason_de,
            "",
            f"– Sophie  [#{key}]",
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
        priority=_LABEL_TO_PRIORITY[match["priority"]],
    )


def findings_from_comments(comments: Sequence[DocComment]) -> list[OpenFinding]:
    results: list[OpenFinding] = []
    for comment in comments:
        if comment.resolved:
            continue
        finding = parse_comment_body(comment.content)
        if finding is not None:
            results.append(OpenFinding(comment_id=comment.id, finding=finding))
    return results
