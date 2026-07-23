from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.services.finding_hygiene import clean_findings, strip_field_name_artifacts


def _finding(
    original: str = "Der Hund schläft.",
    proposed: str = "Der Hund schläft tief.",
    reason: str = "Präzisere Formulierung.",
) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=original, proposed_change=proposed, reason_de=reason),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def test_strips_leaked_field_name_and_restores_the_period() -> None:
    assert (
        strip_field_name_artifacts("Vor dem Doppelpunkt steht kein Leerzeichen..category")
        == "Vor dem Doppelpunkt steht kein Leerzeichen."
    )


def test_strips_the_reason_dot_variant() -> None:
    assert (
        strip_field_name_artifacts("auch hier auf den Bindestrich verzichten.reason.")
        == "auch hier auf den Bindestrich verzichten."
    )


def test_strips_trailing_json_syntax() -> None:
    assert (
        strip_field_name_artifacts("Hier hat sich ein doppeltes ‚i' eingeschlichen.},")
        == "Hier hat sich ein doppeltes ‚i' eingeschlichen."
    )
    assert strip_field_name_artifacts('Kürzer ist klarer."}') == "Kürzer ist klarer."
    assert strip_field_name_artifacts("Kürzer ist klarer.} category") == "Kürzer ist klarer."


def test_sentence_final_quotes_survive() -> None:
    assert strip_field_name_artifacts("Besser wäre ‚das Rezept'.") == "Besser wäre ‚das Rezept'."


def test_strips_chained_and_bare_tokens() -> None:
    assert (
        strip_field_name_artifacts("Kürzer ist klarer. category priority") == "Kürzer ist klarer."
    )
    assert strip_field_name_artifacts("Kürzer ist klarer categorie") == "Kürzer ist klarer"


def test_clean_text_passes_through_untouched() -> None:
    for text in (
        "Präzisere Formulierung.",
        "Die Kategorie stimmt hier nicht ganz.",
        "Eine Priorität hat dieser Satz nicht nötig!",
        "Größe und Maß beachten — überall.",
    ):
        assert strip_field_name_artifacts(text) == text


def test_text_that_is_only_an_artifact_stays_untouched() -> None:
    assert strip_field_name_artifacts("category") == "category"


def test_noop_finding_is_dropped() -> None:
    noop = _finding(original="Zeit: 30 Min.", proposed="Zeit: 30 Min.")
    kept = _finding()

    assert clean_findings([noop, kept]) == [kept]


def test_artifact_that_masked_a_noop_is_dropped_after_stripping() -> None:
    disguised = _finding(original="Zeit: 30 Min.", proposed="Zeit: 30 Min..category")

    assert clean_findings([disguised]) == []


def test_original_text_is_never_modified() -> None:
    finding = _finding(
        original="Der Satz endet mit category",
        proposed="Der Satz endet anders.",
        reason="Klarer.reason.",
    )

    cleaned = clean_findings([finding])[0]

    assert cleaned.suggestion.original_text == "Der Satz endet mit category"
    assert cleaned.suggestion.reason_de == "Klarer."
