from pydantic import BaseModel

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding


class EngineResult(BaseModel):
    # The engine's whole handoff to the orchestrator: located findings, the
    # whole-book report, and whether the run finished (False => budget tripped).
    findings: list[Finding]
    report: ConsistencyReport
    complete: bool
