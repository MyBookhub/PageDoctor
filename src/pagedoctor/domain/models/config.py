from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CheckMode(StrEnum):
    PROOFREADING = "proofreading"
    EDITING = "editing"


class BookType(StrEnum):
    COOKBOOK = "cookbook"
    ADVICE = "advice"
    NOVEL_MEMOIR = "novel_memoir"
    CHILDRENS = "childrens"


class Strictness(StrEnum):
    LIGHT = "light"
    STANDARD = "standard"
    THOROUGH = "thorough"


class CustomDictionary(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed_terms: frozenset[str] = frozenset()


class ReviewConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    modes: frozenset[CheckMode]
    book_type: BookType
    strictness: Strictness
    language: str = "de-DE"
    custom_dictionary: CustomDictionary = Field(default_factory=CustomDictionary)
    recipe_mode: bool = False
