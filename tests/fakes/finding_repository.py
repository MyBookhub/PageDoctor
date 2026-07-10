from collections.abc import Sequence
from datetime import datetime

from pagedoctor.domain.models.stored_finding import FindingStatus, StoredFinding


class InMemoryFindingRepository:
    def __init__(self) -> None:
        # Keyed by (doc_id, key) to mirror the table's identity.
        self._findings: dict[tuple[str, str], StoredFinding] = {}

    def save_findings(self, findings: Sequence[StoredFinding]) -> None:
        for finding in findings:
            self._findings.setdefault((finding.doc_id, finding.key), finding)

    def open_findings(self, doc_id: str) -> list[StoredFinding]:
        return [
            finding
            for (stored_doc, _), finding in self._findings.items()
            if stored_doc == doc_id and finding.status is FindingStatus.OPEN
        ]

    def set_status(self, doc_id: str, comment_id: str, status: FindingStatus) -> None:
        for identity, finding in self._findings.items():
            if finding.doc_id == doc_id and finding.comment_id == comment_id:
                self._findings[identity] = finding.model_copy(update={"status": status})

    def purge_expired(self, cutoff: datetime) -> int:
        expired = [
            identity for identity, finding in self._findings.items() if finding.updated_at < cutoff
        ]
        for identity in expired:
            del self._findings[identity]
        return len(expired)
