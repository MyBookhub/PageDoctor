from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding


class FindingRepositoryPort(Protocol):
    # Findings are stored so BookHub can track suggestions and outcomes without re-parsing
    # Google comments (§9.2). Implementations encrypt the finding-text columns at rest and
    # accept/return plaintext domain models only.

    def save_findings(self, findings: Sequence[StoredFinding]) -> None:
        # Insert findings not already present for their doc; existing rows keep their status
        # (idempotent — a re-review must never reset an applied/dismissed finding to open).
        ...

    def open_findings(self, doc_id: str) -> list[StoredFinding]: ...

    def set_status(self, doc_id: str, comment_id: str, status: FindingStatus) -> None: ...

    def purge_expired(self, cutoff: datetime) -> int: ...
