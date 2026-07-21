from collections.abc import Sequence
from typing import Protocol

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import OutputResult, ReviewRun


class OutputPort(Protocol):
    # Must be idempotent: safe to retry without double-posting (comments) and without
    # creating a duplicate copy (versioned Lektorat copies, issue #31).
    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> OutputResult: ...
