from typing import Protocol

from pagedoctor.domain.models.comment import DocComment


class CommentsSourcePort(Protocol):
    def read_comments(self, doc_id: str) -> list[DocComment]: ...
