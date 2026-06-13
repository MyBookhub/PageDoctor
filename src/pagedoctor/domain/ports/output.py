from collections.abc import Sequence
from typing import Protocol

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.models.run import ReviewRun


class OutputPort(Protocol):
    # The headline swappable seam: v1 posts Drive comments; a later adapter posts
    # native suggestions. Must be idempotent: safe to retry without double-posting
    # (consult the run's per-finding key checkpoint).
    def write_findings(
        self, run: ReviewRun, findings: Sequence[Finding], report: ConsistencyReport
    ) -> None: ...
