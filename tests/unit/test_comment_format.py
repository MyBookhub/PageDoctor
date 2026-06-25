from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.comment_format import (
    format_comment_body,
    parse_comment_body,
)


def _finding(
    original: str = "Der Hund schläft.",
    proposed: str = "Der Hund schläft tief.",
    reason: str = "Präzisere Formulierung.",
    category: Category = Category.PROOFREADING,
    priority: Priority = Priority.FEHLER,
) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=original, proposed_change=proposed, reason_de=reason),
        category=category,
        priority=priority,
    )


def test_format_then_parse_round_trips() -> None:
    finding = _finding()
    assert parse_comment_body(format_comment_body(finding, "0123456789abcdef")) == finding


def test_round_trips_across_categories_and_priorities() -> None:
    for category in Category:
        for priority in Priority:
            finding = _finding(category=category, priority=priority)
            body = format_comment_body(finding, "abcdef0123456789")
            assert parse_comment_body(body) == finding


def test_round_trips_with_umlauts_and_punctuation() -> None:
    finding = _finding(
        original="Der »Hund« schläft, oder?",
        proposed="Der Hund schläft – tief und fest!",
        reason="Gedankenstrich statt Komma; Größe und Maß beachten.",
    )
    assert parse_comment_body(format_comment_body(finding, "0011223344556677")) == finding


def test_round_trips_with_multiline_reason() -> None:
    finding = _finding(reason="Erste Zeile.\nZweite Zeile mit Begründung.")
    assert parse_comment_body(format_comment_body(finding, "1122334455667788")) == finding


def test_parse_ignores_the_consistency_report() -> None:
    body = "\n".join(
        (
            "[Konsistenzbericht]",
            "",
            "Keine Auffälligkeiten gefunden.",
            "",
            "— Sophie Hoffmann  [#abcdef0123456789]",
        )
    )
    assert parse_comment_body(body) is None


def test_parse_ignores_a_plain_human_comment() -> None:
    assert parse_comment_body("Bitte hier nochmal prüfen, danke!") is None


def test_parse_requires_the_marker() -> None:
    body = format_comment_body(_finding(), "0123456789abcdef").replace("  [#0123456789abcdef]", "")
    assert parse_comment_body(body) is None
