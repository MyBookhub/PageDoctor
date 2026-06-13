from pydantic import BaseModel

from pagedoctor.domain.models.consistency import ConsistencyReport
from pagedoctor.domain.models.finding import Finding


class EngineResult(BaseModel):
    findings: list[Finding]
    report: ConsistencyReport
    complete: bool
