from typing import Protocol

from pagedoctor.domain.models.document import SourceDocument


class DocumentSourcePort(Protocol):
    # Re-read fresh on every run; indices are not stable across runs.
    # Raises DocumentAccessDeniedError when the document cannot be read.
    def read(self, doc_id: str) -> SourceDocument: ...
