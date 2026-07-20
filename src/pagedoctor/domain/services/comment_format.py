import re
from collections.abc import Sequence

from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.idempotency import KEY_LENGTH

_CATEGORY_LABELS = {Category.PROOFREADING: "Korrektorat", Category.EDITING: "Lektorat"}
_LABEL_TO_CATEGORY = {label: category for category, label in _CATEGORY_LABELS.items()}

_KEY_RE = rf"[0-9a-f]{{{KEY_LENGTH}}}"

# Matches the idempotency key wherever it appears in a comment (header or, in the legacy
# layout, trailing after the signature) — used to scan already-posted keys (CLAUDE.md §10).
MARKER = re.compile(rf"#({_KEY_RE})")

# Current layout: all structured metadata (category, priority, id) lives in the header
# bracket; the signature line is plain, human-readable text.
_FINDING_COMMENT = re.compile(
    r"\[(?P<label>Korrektorat|Lektorat) · (?P<priority>FEHLER|EMPFEHLUNG|HINWEIS) · "
    rf"#(?P<key>{_KEY_RE})\]\n"
    r"Original: „(?P<original>.*?)“\n"
    r"Vorschlag: „(?P<proposed>.*?)“\n"
    r"Begründung: (?P<reason>.*?)\n"
    r"— Sophie Hoffmann",
    re.DOTALL,
)

# Legacy layout (id trailing after the signature instead of in the header) — findings are
# always re-derived live from Drive comments, never persisted, so comments already posted
# under the old layout must stay parseable or they'd silently vanish from open findings.
_FINDING_COMMENT_LEGACY = re.compile(
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
            f"[{label} · {finding.priority.value} · #{key}]",
            f"Original: „{suggestion.original_text}“",
            f"Vorschlag: „{suggestion.proposed_change}“",
            f"Begründung: {suggestion.reason_de}",
            "— Sophie Hoffmann",
        )
    )


def parse_comment_body(content: str) -> Finding | None:
    match = _FINDING_COMMENT.search(content) or _FINDING_COMMENT_LEGACY.search(content)
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


def findings_from_comments(comments: Sequence[DocComment]) -> list[Finding]:
    findings: list[Finding] = []
    for comment in comments:
        if comment.resolved:
            continue
        finding = parse_comment_body(comment.content)
        if finding is not None:
            findings.append(finding)
    return findings
