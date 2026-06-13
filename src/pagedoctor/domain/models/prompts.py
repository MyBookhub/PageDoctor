from pydantic import BaseModel, ConfigDict


class PromptBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    # The stable, cacheable system prefix. The volatile chunk text is added to the
    # user message by the adapter and never enters this bundle.
    system_blocks: tuple[str, ...]

    def joined(self) -> str:
        return "\n\n".join(self.system_blocks)
