import hashlib

from pagedoctor.domain.models.finding import Suggestion

KEY_LENGTH = 16
_SEP = "\x00"


def finding_key(doc_id: str, suggestion: Suggestion) -> str:
    # Category/priority are not part of a finding's identity: they no longer appear in the
    # posted comment text (Sophie's voice, no labels/brackets), so they can't be re-derived
    # when re-scanning existing Drive comments — only the quote and proposed change can.
    material = _SEP.join((doc_id, suggestion.original_text, suggestion.proposed_change))
    return _digest(material)


def consistency_report_key(doc_id: str) -> str:
    return _digest(_SEP.join((doc_id, "consistency-report")))


def _digest(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:KEY_LENGTH]
