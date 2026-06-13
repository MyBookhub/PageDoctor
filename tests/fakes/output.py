from collections.abc import Sequence

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import ReviewRun
from pagedoctor.domain.services.idempotency import consistency_report_key, finding_key


class FakeOutputPort:
    def __init__(self) -> None:
        self.posted: dict[str, str] = {}

    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> None:
        already = set(run.posted_finding_keys) | set(self.posted)
        for finding in findings:
            key = finding_key(run.doc_id, finding)
            if key in already:
                continue
            self.posted[key] = finding.suggestion.proposed_change
            already.add(key)
        report_key = consistency_report_key(run.doc_id)
        if report_key not in already:
            self.posted[report_key] = "consistency-report"
