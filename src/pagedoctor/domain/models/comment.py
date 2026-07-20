from pydantic import BaseModel, ConfigDict


class DocComment(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    resolved: bool
    id: str | None = None
