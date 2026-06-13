from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.document import IndexMap, SourceDocument
from pagedoctor.domain.services.consistency import build_consistency_report


def _doc(text: str) -> SourceDocument:
    return SourceDocument(doc_id="d", text=text, index_map=IndexMap(plain_text_length=len(text)))


def _config(allowed: frozenset[str] = frozenset()) -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.EDITING}),
        book_type=BookType.COOKBOOK,
        strictness=Strictness.STANDARD,
        custom_dictionary=CustomDictionary(allowed_terms=allowed),
    )


def test_spelling_variants_cluster_near_duplicates() -> None:
    text = "Das Basilikum ist gut. Spaeter kommt das Baslikum noch dazu, viel Basilikum."
    report = build_consistency_report(_doc(text), _config())
    clusters = [{v.canonical, *v.variants} for v in report.spelling_variants]
    assert any({"Basilikum", "Baslikum"} <= cluster for cluster in clusters)


def test_term_variants_catch_inconsistent_rendering() -> None:
    text = "Schreib eine E-Mail. Dann noch eine Email und eine weitere E-Mail."
    report = build_consistency_report(_doc(text), _config())
    surfaces = [{v.canonical, *v.variants} for v in report.term_variants]
    assert any({"E-Mail", "Email"} <= group for group in surfaces)


def test_per_chapter_repetition_is_reported() -> None:
    text = (
        "Kapitel 1\n\n"
        "Lecker lecker lecker lecker schmeckt das Gericht wunderbar lecker.\n\n"
        "Kapitel 2\n\n"
        "Hier steht etwas voellig anderes ohne Wiederholung."
    )
    report = build_consistency_report(_doc(text), _config())
    lecker = [s for s in report.repetition_stats if s.term == "lecker"]
    assert lecker and lecker[0].count >= 4
    assert lecker[0].chapter is not None and "Kapitel 1" in lecker[0].chapter


def test_custom_dictionary_suppresses_findings() -> None:
    text = "Das Basilikum ist gut. Spaeter kommt das Baslikum noch dazu, viel Basilikum."
    report = build_consistency_report(_doc(text), _config(allowed=frozenset({"Baslikum"})))
    flagged = {s.casefold() for v in report.spelling_variants for s in {v.canonical, *v.variants}}
    assert "baslikum" not in flagged


def test_report_is_always_produced_even_when_clean() -> None:
    report = build_consistency_report(_doc("Ein sauberer kurzer Satz."), _config())
    assert report.term_variants == []
    assert report.spelling_variants == []
