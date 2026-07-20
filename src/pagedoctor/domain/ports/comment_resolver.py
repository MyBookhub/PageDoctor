from typing import Protocol


class CommentResolverPort(Protocol):
    def resolve_comment(self, doc_id: str, comment_id: str) -> None: ...
