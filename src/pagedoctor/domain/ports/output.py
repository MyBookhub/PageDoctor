from collections.abc import Sequence
from typing import Protocol

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import ReviewRun


class OutputPort(Protocol):
    # Must be idempotent: safe to retry without double-posting.
    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> None: ...
