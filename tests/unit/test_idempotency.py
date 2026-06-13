from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key


def _finding(
    original: str = "Der Hund schläft.",
    change: str = "Der Hund schläft tief.",
    category: Category = Category.PROOFREADING,
) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=original, proposed_change=change, reason_de="r"),
        category=category,
        priority=Priority.FEHLER,
    )


def test_same_finding_same_doc_is_stable() -> None:
    assert finding_key("doc-1", _finding()) == finding_key("doc-1", _finding())


def test_key_is_short_lowercase_hex() -> None:
    key = finding_key("doc-1", _finding())
    assert len(key) == 16
    assert all(char in "0123456789abcdef" for char in key)


def test_different_doc_changes_key() -> None:
    assert finding_key("doc-1", _finding()) != finding_key("doc-2", _finding())


def test_different_quote_change_or_category_changes_key() -> None:
    base = finding_key("doc-1", _finding())
    assert base != finding_key("doc-1", _finding(original="Die Katze schläft."))
    assert base != finding_key("doc-1", _finding(change="Der Hund schläft fest."))
    assert base != finding_key("doc-1", _finding(category=Category.EDITING))


def test_reason_does_not_affect_key() -> None:
    a = Finding(
        suggestion=Suggestion(original_text="a", proposed_change="b", reason_de="erste"),
        category=Category.EDITING,
        priority=Priority.HINWEIS,
    )
    b = a.model_copy(update={"suggestion": a.suggestion.model_copy(update={"reason_de": "zweite"})})
    assert finding_key("doc-1", a) == finding_key("doc-1", b)


def test_consistency_report_key_stable_and_doc_scoped() -> None:
    assert consistency_report_key("doc-1") == consistency_report_key("doc-1")
    assert consistency_report_key("doc-1") != consistency_report_key("doc-2")
