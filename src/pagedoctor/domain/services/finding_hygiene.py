import re

from pagedoctor.domain.models.finding import Finding

# The model occasionally leaks structured-output residue into the end of its free-text
# fields despite the prompt forbidding it: field names ("…kein Leerzeichen..category",
# "…prüfen.reason.") and JSON syntax ("…eingeschlichen.},"). Stripping is confined to
# these exact trailing shapes; original_text is never touched — it must stay byte-exact
# for quote-and-locate (issue #40).
_FIELD_NAME_ARTIFACT = re.compile(
    r"(?:[\s.]*\b(?:original_text|proposed_change|reason_de|reason|category|categorie|priority)\b\.?)+\s*$",
    re.IGNORECASE,
)
# Braces never end legitimate German prose; commas/quotes are stripped only when they
# accompany a brace, so ordinary sentence-final punctuation stays intact.
_JSON_ARTIFACT = re.compile(r"[\s,\"']*[}{]+[\s,\"'}{]*$")
_SENTENCE_END = (".", "!", "?", "…", "“", "‘", '"')


def strip_field_name_artifacts(text: str) -> str:
    # Residue stacks in mixed shapes ("….} category"), so strip to a fixpoint: each pass
    # removes at most one artifact layer, and a pass that changes nothing ends the loop.
    cleaned = text
    while True:
        step = strip_one_artifact_layer(cleaned)
        if step == cleaned:
            return cleaned
        cleaned = step


def strip_one_artifact_layer(text: str) -> str:
    without_json = _JSON_ARTIFACT.sub("", text).rstrip()
    if without_json and without_json != text:
        return without_json
    match = _FIELD_NAME_ARTIFACT.search(text)
    if match is None:
        return text
    stripped = text[: match.start()].rstrip()
    if not stripped:
        return text
    # The artifact often swallows the sentence period ("Leerzeichen..category" carries the
    # sentence dot inside the match) — restore it when the artifact began with one.
    if match.group(0).lstrip().startswith(".") and not stripped.endswith(_SENTENCE_END):
        return f"{stripped}."
    return stripped


def clean_findings(findings: list[Finding]) -> list[Finding]:
    # Drops no-op findings (proposal identical to the quote — the model hallucinating a
    # change that does not exist) and scrubs leaked field names from the editable fields.
    cleaned: list[Finding] = []
    for finding in findings:
        suggestion = finding.suggestion
        proposed = strip_field_name_artifacts(suggestion.proposed_change)
        reason = strip_field_name_artifacts(suggestion.reason_de)
        if suggestion.original_text == proposed:
            continue
        cleaned.append(
            finding.model_copy(
                update={
                    "suggestion": suggestion.model_copy(
                        update={"proposed_change": proposed, "reason_de": reason}
                    )
                }
            )
        )
    return cleaned
