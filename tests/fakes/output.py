from collections.abc import Sequence

from pagedoctor.domain.errors import CommentPostingError
from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import ReviewRun
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key


class FakeOutputPort:
    def __init__(self, fail_after: int | None = None) -> None:
        self.posted: dict[str, str] = {}
        # Every key handed to create, including across runs: a repeat here is a double-post.
        self.post_log: list[str] = []
        self.resolved: set[str] = set()
        self._fail_after = fail_after

    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> None:
        already = set(run.posted_finding_keys) | set(self.posted)
        for finding in findings:
            key = finding_key(run.doc_id, finding)
            if key in already:
                continue
            self.post(key, finding.suggestion.proposed_change)
            already.add(key)
        report_key = consistency_report_key(run.doc_id)
        if report_key not in already:
            self.post(report_key, "consistency-report")

    def resolve_comment(self, doc_id: str, comment_id: str) -> None:
        self.resolved.add(comment_id)

    def post(self, key: str, value: str) -> None:
        if self._fail_after is not None and len(self.post_log) >= self._fail_after:
            # Simulate a crash mid-write: comments already posted survive in the doc.
            raise CommentPostingError("simulated mid-write failure")
        self.post_log.append(key)
        self.posted[key] = value
