from pydantic import BaseModel, ConfigDict


class PromptBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_blocks: tuple[str, ...]

    def joined(self) -> str:
        return "\n\n".join(self.system_blocks)
