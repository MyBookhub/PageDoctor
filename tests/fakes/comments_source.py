from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.comment import DocComment


class FakeCommentsSource:
    def __init__(self, comments: dict[str, list[DocComment]] | None = None) -> None:
        self._comments = comments or {}
        self.reads: list[str] = []

    def read_comments(self, doc_id: str) -> list[DocComment]:
        self.reads.append(doc_id)
        comments = self._comments.get(doc_id)
        if comments is None:
            raise DocumentAccessDeniedError(doc_id)
        return list(comments)
