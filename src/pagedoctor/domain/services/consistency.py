import re
from collections import Counter, defaultdict
from collections.abc import Iterable

from pagedoctor.domain.models.config import ReviewConfig
from pagedoctor.domain.models.consistency import (
    ConsistencyReport,
    RepetitionStat,
    TermVariant,
)
from pagedoctor.domain.models.document import SourceDocument

_WORD = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß-]*")
_CHAPTER_HEADING = re.compile(r"(?mi)^\s*(?:kapitel|chapter)\b.*$")
_NON_ALNUM = re.compile(r"[^0-9a-zäöüß]")

_REPETITION_THRESHOLD = 4
_MIN_VARIANT_LENGTH = 4
_MAX_EDIT_DISTANCE = 2

_STOPWORDS = frozenset(
    {
        "aber",
        "auch",
        "auf",
        "aus",
        "bei",
        "dann",
        "das",
        "dass",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "dies",
        "diese",
        "dieser",
        "dieses",
        "durch",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "eines",
        "für",
        "haben",
        "hatte",
        "hier",
        "ist",
        "kann",
        "können",
        "mehr",
        "mit",
        "nach",
        "nicht",
        "noch",
        "nur",
        "oder",
        "schon",
        "sehr",
        "sein",
        "seine",
        "sich",
        "sind",
        "über",
        "und",
        "unter",
        "von",
        "war",
        "werden",
        "wenn",
        "wie",
        "wird",
        "zum",
        "zur",
    }
)


def build_consistency_report(document: SourceDocument, config: ReviewConfig) -> ConsistencyReport:
    allowed = {term.casefold() for term in config.custom_dictionary.allowed_terms}
    frequency = _word_frequency(document.text, allowed)
    return ConsistencyReport(
        term_variants=_term_variants(frequency),
        spelling_variants=_spelling_variants(frequency),
        repetition_stats=_repetition_stats(document.text, allowed),
    )


def _word_frequency(text: str, allowed: set[str]) -> Counter[str]:
    return Counter(word for word in _WORD.findall(text) if word.casefold() not in allowed)


def _normalize(word: str) -> str:
    return _NON_ALNUM.sub("", word.casefold())


def _term_variants(frequency: Counter[str]) -> list[TermVariant]:
    # Same normalized key, different surface forms = the term is rendered
    # inconsistently (case / hyphen / spacing), e.g. "E-Mail" vs "Email".
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for word, count in frequency.items():
        grouped[_normalize(word)][word] += count
    return _to_variants(surfaces for surfaces in grouped.values() if len(surfaces) > 1)


def _spelling_variants(frequency: Counter[str]) -> list[TermVariant]:
    # Distinct normalized keys that are within a small edit distance = likely
    # misspellings of one word, e.g. "Basilikum" vs "Baslikum".
    representative: dict[str, Counter[str]] = defaultdict(Counter)
    for word, count in frequency.items():
        key = _normalize(word)
        if len(key) >= _MIN_VARIANT_LENGTH:
            representative[key][word] += count

    clusters = _cluster_by_edit_distance(list(representative))
    groups: list[Counter[str]] = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        merged: Counter[str] = Counter()
        for key in cluster:
            merged.update(representative[key])
        groups.append(merged)
    return _to_variants(groups)


def _cluster_by_edit_distance(keys: list[str]) -> list[list[str]]:
    buckets: dict[tuple[str, int], list[str]] = defaultdict(list)
    for key in keys:
        buckets[(key[0], len(key))].append(key)

    parent = {key: key for key in keys}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for key in keys:
        for length in (len(key), len(key) + 1, len(key) + 2):
            for other in buckets.get((key[0], length), ()):
                if other != key and _within_edit_distance(key, other, _MAX_EDIT_DISTANCE):
                    parent[find(key)] = find(other)

    clustered: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        clustered[find(key)].append(key)
    return list(clustered.values())


def _within_edit_distance(left: str, right: str, limit: int) -> bool:
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        if min(current) > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _to_variants(groups: Iterable[Counter[str]]) -> list[TermVariant]:
    variants: list[TermVariant] = []
    for surfaces in groups:
        canonical = surfaces.most_common(1)[0][0]
        others = frozenset(surface for surface in surfaces if surface != canonical)
        variants.append(
            TermVariant(canonical=canonical, variants=others, occurrences=sum(surfaces.values()))
        )
    return sorted(variants, key=lambda variant: variant.canonical)


def _repetition_stats(text: str, allowed: set[str]) -> list[RepetitionStat]:
    stats: list[RepetitionStat] = []
    for chapter, section in _chapters(text):
        counts = Counter(
            word.casefold()
            for word in _WORD.findall(section)
            if len(word) >= _MIN_VARIANT_LENGTH
            and word.casefold() not in _STOPWORDS
            and word.casefold() not in allowed
        )
        for term, count in counts.items():
            if count >= _REPETITION_THRESHOLD:
                stats.append(RepetitionStat(term=term, count=count, chapter=chapter))
    return sorted(stats, key=lambda stat: (stat.chapter or "", -stat.count, stat.term))


def _chapters(text: str) -> list[tuple[str | None, str]]:
    headings = list(_CHAPTER_HEADING.finditer(text))
    if not headings:
        return [(None, text)]
    sections: list[tuple[str | None, str]] = []
    if headings[0].start() > 0:
        sections.append((None, text[: headings[0].start()]))
    for current, following in zip(headings, [*headings[1:], None], strict=False):
        end = following.start() if following else len(text)
        label = current.group(0).strip()
        sections.append((label, text[current.start() : end]))
    return sections
