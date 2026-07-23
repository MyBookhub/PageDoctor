from fakes.llm import FakeLlmProvider
from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.document import IndexMap, SourceDocument
from pagedoctor.domain.models.finding import (
    Category,
    ChunkFindings,
    Finding,
    Priority,
    Suggestion,
)
from pagedoctor.domain.services.engine import EditingEngine


def _doc(text: str) -> SourceDocument:
    return SourceDocument(doc_id="d", text=text, index_map=IndexMap(plain_text_length=len(text)))


def _config() -> ReviewConfig:
    return ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )


def _finding(quote: str) -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=quote, proposed_change="x", reason_de="y"),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def test_run_locates_findings_and_builds_report() -> None:
    document = _doc("Der Hund ist braun. Die Katze schlaeft.")
    provider = FakeLlmProvider(
        responses={0: ChunkFindings(findings=[_finding("ist braun"), _finding("fehlt im Text")])}
    )
    result = EditingEngine(provider).run(document, _config())
    assert result.complete is True
    assert len(result.findings) == 2
    assert result.findings[0].located is not None
    assert result.findings[1].located is None
    assert result.report is not None


def test_run_stops_and_marks_incomplete_when_budget_trips() -> None:
    document = _doc("\n\n".join(f"Absatz {n} mit etwas Inhalt zum Fuellen." for n in range(400)))
    provider = FakeLlmProvider(
        responses={0: ChunkFindings(findings=[_finding("Absatz 0 mit etwas Inhalt")])},
        budget_after=1,
    )
    result = EditingEngine(provider).run(document, _config())
    assert result.complete is False
    assert len(provider.calls) == 1
    assert len(result.findings) == 1
    assert result.report is not None


def test_run_on_empty_document_is_complete_with_no_findings() -> None:
    result = EditingEngine(FakeLlmProvider()).run(_doc(""), _config())
    assert result.complete is True
    assert result.findings == []


def test_rolling_memory_feeds_previous_findings_into_the_next_chunk() -> None:
    # Two chunks: the first call gets an empty window, the second sees chunk one's
    # (hygiene-cleaned) findings (issue #41).
    document = _doc("\n\n".join(f"Absatz {n} mit etwas Inhalt zum Fuellen." for n in range(400)))
    first = _finding("Absatz 0 mit etwas Inhalt")
    provider = FakeLlmProvider(responses={0: ChunkFindings(findings=[first])})

    EditingEngine(provider).run(document, _config())

    assert len(provider.recent_windows) >= 2
    assert provider.recent_windows[0] == ()
    second_window = provider.recent_windows[1]
    assert len(second_window) == 1
    assert second_window[0].suggestion.original_text == "Absatz 0 mit etwas Inhalt"
