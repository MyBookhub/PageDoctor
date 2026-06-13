from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from pagedoctor.domain.models.document import LocatedSpan


class Priority(StrEnum):
    FEHLER = "FEHLER"
    EMPFEHLUNG = "EMPFEHLUNG"
    HINWEIS = "HINWEIS"


class Category(StrEnum):
    PROOFREADING = "proofreading"
    EDITING = "editing"


class Suggestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_text: str
    proposed_change: str
    reason_de: str


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: Suggestion
    category: Category
    priority: Priority
    located: LocatedSpan | None = None


class ChunkFindings(BaseModel):
    findings: list[Finding]
