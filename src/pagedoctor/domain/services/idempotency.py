import hashlib

from pagedoctor.domain.models.finding import Finding

KEY_LENGTH = 16
_SEP = "\x00"


def finding_key(doc_id: str, finding: Finding) -> str:
    suggestion = finding.suggestion
    material = _SEP.join(
        (
            doc_id,
            suggestion.original_text,
            suggestion.proposed_change,
            finding.category.value,
        )
    )
    return _digest(material)


def consistency_report_key(doc_id: str) -> str:
    return _digest(_SEP.join((doc_id, "consistency-report")))


def _digest(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:KEY_LENGTH]
