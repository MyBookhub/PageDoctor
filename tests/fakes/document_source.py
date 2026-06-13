from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.document import SourceDocument


class FakeDocumentSource:
    def __init__(self, documents: dict[str, SourceDocument] | None = None) -> None:
        self._documents = documents or {}
        self.reads: list[str] = []

    def read(self, doc_id: str) -> SourceDocument:
        self.reads.append(doc_id)
        document = self._documents.get(doc_id)
        if document is None:
            raise DocumentAccessDeniedError(doc_id)
        return document
