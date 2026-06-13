from typing import Protocol

from pagedoctor.domain.models.document import SourceDocument


class DocumentSourcePort(Protocol):
    def read(self, doc_id: str) -> SourceDocument: ...
