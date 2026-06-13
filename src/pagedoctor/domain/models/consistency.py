from pydantic import BaseModel, ConfigDict


class TermVariant(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical: str
    variants: frozenset[str]
    occurrences: int


class RepetitionStat(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str
    count: int
    chapter: str | None = None


class ConsistencyReport(BaseModel):
    term_variants: list[TermVariant]
    spelling_variants: list[TermVariant]
    repetition_stats: list[RepetitionStat]
