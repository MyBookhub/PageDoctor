from pagedoctor.domain.models.config import (
    BookType,
    CheckMode,
    CustomDictionary,
    ReviewConfig,
    Strictness,
)
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.prompts.builder import (
    CACHE_MIN_TOKENS,
    RECENT_FINDINGS_IN_PROMPT,
    build_prompt_bundle,
    build_user_message,
    estimate_tokens,
)


def _config(
    *,
    modes: frozenset[CheckMode] = frozenset({CheckMode.PROOFREADING}),
    book_type: BookType = BookType.NOVEL_MEMOIR,
    strictness: Strictness = Strictness.STANDARD,
    recipe_mode: bool = False,
    allowed: frozenset[str] = frozenset(),
) -> ReviewConfig:
    return ReviewConfig(
        modes=modes,
        book_type=book_type,
        strictness=strictness,
        recipe_mode=recipe_mode,
        custom_dictionary=CustomDictionary(allowed_terms=allowed),
    )


def test_cached_prefix_clears_the_token_floor() -> None:
    bundle = build_prompt_bundle(
        _config(book_type=BookType.NOVEL_MEMOIR, strictness=Strictness.LIGHT)
    )
    assert estimate_tokens(bundle.joined()) >= CACHE_MIN_TOKENS


def test_book_type_block_switches() -> None:
    cookbook = build_prompt_bundle(_config(book_type=BookType.COOKBOOK)).joined()
    children = build_prompt_bundle(_config(book_type=BookType.CHILDRENS)).joined()
    assert "Kochbuch" in cookbook and "Kochbuch" not in children
    assert "Kinderbuch" in children


def test_strictness_block_switches() -> None:
    light = build_prompt_bundle(_config(strictness=Strictness.LIGHT)).joined()
    thorough = build_prompt_bundle(_config(strictness=Strictness.THOROUGH)).joined()
    assert "ausschließlich echte Fehler" in light
    assert "Lesbarkeit" in thorough


def test_recipe_block_only_for_cookbook_with_recipe_mode() -> None:
    on = build_prompt_bundle(_config(book_type=BookType.COOKBOOK, recipe_mode=True)).joined()
    off = build_prompt_bundle(_config(book_type=BookType.COOKBOOK, recipe_mode=False)).joined()
    wrong_type = build_prompt_bundle(
        _config(book_type=BookType.NOVEL_MEMOIR, recipe_mode=True)
    ).joined()
    assert "Rezeptmodus" in on
    assert "Rezeptmodus" not in off
    assert "Rezeptmodus" not in wrong_type


def test_dictionary_terms_appear_only_when_present() -> None:
    with_terms = build_prompt_bundle(_config(allowed=frozenset({"Schmackofatz"}))).joined()
    without = build_prompt_bundle(_config()).joined()
    assert "Schmackofatz" in with_terms
    assert "Eigenes Wörterbuch" not in without


def test_active_modes_are_described() -> None:
    proofreading = build_prompt_bundle(_config(modes=frozenset({CheckMode.PROOFREADING}))).joined()
    editing = build_prompt_bundle(_config(modes=frozenset({CheckMode.EDITING}))).joined()
    assert "ausschließlich das Korrektorat" in proofreading
    assert "ausschließlich das Lektorat" in editing


def test_builder_is_deterministic() -> None:
    config = _config(book_type=BookType.COOKBOOK, recipe_mode=True, allowed=frozenset({"abc"}))
    assert build_prompt_bundle(config).system_blocks == build_prompt_bundle(config).system_blocks


def _memory_finding(quote: str, proposed: str = "besser") -> Finding:
    return Finding(
        suggestion=Suggestion(original_text=quote, proposed_change=proposed, reason_de="r"),
        category=Category.PROOFREADING,
        priority=Priority.FEHLER,
    )


def test_user_message_without_recent_findings_is_the_bare_chunk() -> None:
    assert build_user_message("Der Text.", ()) == "Der Text."


def test_user_message_lists_recent_findings_before_the_chunk() -> None:
    message = build_user_message("Der Text.", [_memory_finding("Fussili", "Fusilli")])

    assert message.startswith("Deine letzten Anmerkungen")
    assert "„Fussili“ → „Fusilli“" in message
    assert message.endswith("Der zu prüfende Abschnitt:\nDer Text.")


def test_user_message_caps_the_memory_window() -> None:
    findings = [_memory_finding(f"Zitat {n}") for n in range(RECENT_FINDINGS_IN_PROMPT + 5)]

    message = build_user_message("Der Text.", findings)

    assert "Zitat 0" not in message
    assert f"Zitat {RECENT_FINDINGS_IN_PROMPT + 4}" in message
    assert message.count("→") == RECENT_FINDINGS_IN_PROMPT
