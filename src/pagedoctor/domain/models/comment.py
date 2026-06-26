from pydantic import BaseModel, ConfigDict

from pagedoctor.domain.models.finding import Finding


class DocComment(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    content: str
    resolved: bool


class OpenFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    comment_id: str
    finding: Finding
