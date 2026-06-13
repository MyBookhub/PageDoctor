from uuid import UUID

import pytest
from pydantic import ValidationError

from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.consistency import (
    ConsistencyReport,
    RepetitionStat,
    TermVariant,
)
from pagedoctor.domain.models.document import (
    IndexMap,
    LocatedSpan,
    SourceDocument,
    TextChunk,
)
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.models.run import ReviewRun, RunStatus


def test_value_objects_are_frozen() -> None:
    span = LocatedSpan(quote="Rezpet", start=0, end=6)
    with pytest.raises(ValidationError):
        span.start = 5  # type: ignore[misc]


def test_enum_members() -> None:
    assert set(Priority) == {Priority.FEHLER, Priority.EMPFEHLUNG, Priority.HINWEIS}
    assert set(CheckMode) == {CheckMode.PROOFREADING, CheckMode.EDITING}
    assert set(Category) == {Category.PROOFREADING, Category.EDITING}
    assert set(BookType) == {
        BookType.COOKBOOK,
        BookType.ADVICE,
        BookType.NOVEL_MEMOIR,
        BookType.CHILDRENS,
    }
    assert set(Strictness) == {Strictness.LIGHT, Strictness.STANDARD, Strictness.THOROUGH}
    assert set(RunStatus) == {
        RunStatus.PENDING,
        RunStatus.RUNNING,
        RunStatus.WRITING,
        RunStatus.DONE,
        RunStatus.INCOMPLETE,
        RunStatus.FAILED,
    }


def test_review_config_defaults() -> None:
    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.COOKBOOK,
        strictness=Strictness.STANDARD,
    )
    assert config.language == "de-DE"
    assert config.recipe_mode is False
    assert config.custom_dictionary == CustomDictionary()


def test_finding_and_chunk_findings_construct() -> None:
    located = LocatedSpan(quote="Rezpet", start=0, end=6)
    finding = Finding(
        suggestion=Suggestion(
            original_text="Rezpet", proposed_change="Rezept", reason_de="Tippfehler"
        ),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
        located=located,
    )
    wrapper = ChunkFindings(findings=[finding])
    assert wrapper.findings[0].located == located


def test_consistency_and_document_models() -> None:
    report = ConsistencyReport(
        term_variants=[
            TermVariant(canonical="Basilikum", variants=frozenset({"Baslikum"}), occurrences=3)
        ],
        spelling_variants=[],
        repetition_stats=[RepetitionStat(term="lecker", count=4, chapter="1")],
    )
    assert report.term_variants[0].occurrences == 3

    doc = SourceDocument(doc_id="abc", text="hallo", index_map=IndexMap(plain_text_length=5))
    chunk = TextChunk(index=0, text="hallo", start_offset=0, end_offset=5)
    assert doc.index_map.segments == ()
    assert chunk.end_offset == 5


def test_review_run_is_metadata_only() -> None:
    run = ReviewRun(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        doc_id="abc",
        config=ReviewConfig(
            modes=frozenset({CheckMode.EDITING}),
            book_type=BookType.NOVEL_MEMOIR,
            strictness=Strictness.THOROUGH,
        ),
        status=RunStatus.PENDING,
        correlation_id="corr-1",
    )
    assert run.status is RunStatus.PENDING
    assert run.posted_finding_keys == frozenset()
    assert run.token_budget is None
