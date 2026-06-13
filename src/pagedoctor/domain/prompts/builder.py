from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig
from pagedoctor.domain.models.prompts import PromptBundle
from pagedoctor.domain.prompts.templates.book_type import BOOK_TYPE_INSTRUCTIONS
from pagedoctor.domain.prompts.templates.guide import CORRECTION_GUIDE
from pagedoctor.domain.prompts.templates.output_contract import OUTPUT_CONTRACT
from pagedoctor.domain.prompts.templates.persona import PERSONA
from pagedoctor.domain.prompts.templates.recipe import RECIPE
from pagedoctor.domain.prompts.templates.strictness import STRICTNESS_INSTRUCTIONS

# Opus 4.8 only caches a prefix of at least this many tokens; a shorter prefix
# silently does not cache. The real check is the gated live cache test.
CACHE_MIN_TOKENS = 4096


def estimate_tokens(text: str) -> int:
    # 2.5 chars/token: a safe lower bound for German (measured ~2), so this never
    # over-counts. The real floor is the gated live cache test.
    return len(text) * 2 // 5


def build_prompt_bundle(config: ReviewConfig) -> PromptBundle:
    blocks: list[str] = [
        PERSONA,
        _mode_block(config),
        BOOK_TYPE_INSTRUCTIONS[config.book_type],
        STRICTNESS_INSTRUCTIONS[config.strictness],
        CORRECTION_GUIDE,
    ]
    dictionary = _dictionary_block(config)
    if dictionary is not None:
        blocks.append(dictionary)
    if config.book_type == BookType.COOKBOOK and config.recipe_mode:
        blocks.append(RECIPE)
    blocks.append(OUTPUT_CONTRACT)
    return PromptBundle(system_blocks=tuple(blocks))


def _mode_block(config: ReviewConfig) -> str:
    proofreading = CheckMode.PROOFREADING in config.modes
    editing = CheckMode.EDITING in config.modes
    if proofreading and editing:
        scope = (
            "Du prüfst sowohl das Korrektorat (Rechtschreibung, Grammatik, "
            "Zeichensetzung) als auch das Lektorat (Stil, Formulierung, Wiederholung, "
            "Lesbarkeit)."
        )
    elif proofreading:
        scope = (
            "Du prüfst ausschließlich das Korrektorat: Rechtschreibung, Grammatik, "
            "Zeichensetzung und Tippfehler. Reine Stilfragen lässt du unangetastet."
        )
    elif editing:
        scope = (
            "Du prüfst ausschließlich das Lektorat: Stil, Formulierung, "
            "Wortwiederholung und Lesbarkeit. Reine Rechtschreib- und Grammatikfehler "
            "stehen nicht im Mittelpunkt."
        )
    else:
        scope = "Es ist kein Prüfmodus aktiv; melde nichts."
    return f"Prüfmodus.\n\n{scope}"


def _dictionary_block(config: ReviewConfig) -> str | None:
    terms = sorted(config.custom_dictionary.allowed_terms)
    if not terms:
        return None
    listed = ", ".join(terms)
    return (
        "Eigenes Wörterbuch.\n\n"
        "Die folgenden Wörter sind ausdrücklich korrekt und gewollt (eigene Namen, "
        "Markennamen, Dialekt, bewusste Schreibweisen). Behandle sie als richtig und "
        f"markiere sie niemals als Fehler: {listed}."
    )
