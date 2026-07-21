from pagedoctor.domain.models.comment import DocComment
from pagedoctor.domain.models.finding import Suggestion
from pagedoctor.domain.services.comment_format import (
    format_comment_body,
    open_suggestions,
    parse_comment_body,
)


def _suggestion(
    original: str = "Der Hund schläft.",
    proposed: str = "Der Hund schläft tief.",
    reason: str = "Präzisere Formulierung.",
) -> Suggestion:
    return Suggestion(original_text=original, proposed_change=proposed, reason_de=reason)


def test_format_then_parse_round_trips() -> None:
    suggestion = _suggestion()
    assert parse_comment_body(format_comment_body(suggestion)) == suggestion


def test_round_trips_with_umlauts_and_punctuation() -> None:
    suggestion = _suggestion(
        original="Der »Hund« schläft, oder?",
        proposed="Der Hund schläft – tief und fest!",
        reason="Gedankenstrich statt Komma; Größe und Maß beachten.",
    )
    assert parse_comment_body(format_comment_body(suggestion)) == suggestion


def test_round_trips_with_multiline_reason() -> None:
    suggestion = _suggestion(reason="Erste Zeile.\nZweite Zeile mit Begründung.")
    assert parse_comment_body(format_comment_body(suggestion)) == suggestion


def test_format_carries_no_visible_id_label_or_signature() -> None:
    body = format_comment_body(_suggestion())
    assert "#" not in body
    assert "[" not in body
    assert "]" not in body
    assert "Sophie" not in body
    assert body.startswith("Original: „Der Hund schläft.“\n")
    assert body.endswith("Begründung: Präzisere Formulierung.")


def test_parse_ignores_the_consistency_report() -> None:
    body = "\n".join(
        (
            "Konsistenzbericht",
            "",
            "Keine Auffälligkeiten gefunden.",
            "",
            "— Sophie Hoffmann",
        )
    )
    assert parse_comment_body(body) is None


def test_parse_ignores_a_plain_human_comment() -> None:
    assert parse_comment_body("Bitte hier nochmal prüfen, danke!") is None


def test_parse_still_accepts_the_signature_and_header_layout() -> None:
    # Shipped briefly before the signature/header were dropped entirely. Real docs may still
    # hold comments in this shape; findings are re-derived live, never persisted, so it must
    # stay parseable or those open findings would silently disappear.
    body = "\n".join(
        (
            "Korrektorat · Fehler",
            "Original: „Der Hund schläft.“",
            "Vorschlag: „Der Hund schläft tief.“",
            "Begründung: Präzisere Formulierung.",
            "— Sophie Hoffmann",
        )
    )
    assert parse_comment_body(body) == _suggestion()


def test_parse_still_accepts_the_very_first_layout() -> None:
    # The very first layout ever shipped: category/priority in a bracket, plus a trailing
    # idempotency key after the signature. Same reasoning as above — must stay parseable.
    body = "\n".join(
        (
            "[Korrektorat · FEHLER]",
            "Original: „Der Hund schläft.“",
            "Vorschlag: „Der Hund schläft tief.“",
            "Begründung: Präzisere Formulierung.",
            "— Sophie Hoffmann  [#0123456789abcdef]",
        )
    )
    assert parse_comment_body(body) == _suggestion()


def test_open_suggestions_keeps_open_findings_in_order() -> None:
    first = _suggestion(original="Erstes Zitat.")
    second = _suggestion(original="Zweites Zitat.")
    comments = [
        DocComment(content=format_comment_body(first), resolved=False),
        DocComment(content=format_comment_body(second), resolved=False),
    ]
    assert open_suggestions(comments) == [first, second]


def test_open_suggestions_drops_resolved_and_unparseable() -> None:
    suggestion = _suggestion()
    comments = [
        DocComment(content=format_comment_body(suggestion), resolved=False),
        DocComment(
            content=format_comment_body(_suggestion(original="Erledigt.")),
            resolved=True,
        ),
        DocComment(content="Nur ein menschlicher Kommentar.", resolved=False),
    ]
    assert open_suggestions(comments) == [suggestion]
