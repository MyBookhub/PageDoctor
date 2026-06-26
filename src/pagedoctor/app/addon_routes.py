from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from pagedoctor.app.addon_auth import require_addon_token
from pagedoctor.app.container import get_container
from pagedoctor.domain.errors import DocumentAccessDeniedError
from pagedoctor.domain.models.comment import OpenFinding
from pagedoctor.domain.models.finding import Category, Priority
from pagedoctor.domain.services.comment_format import findings_from_comments
from pagedoctor.domain.services.idempotency import finding_key
from pagedoctor.logging import get_logger

logger = get_logger(__name__)

addon_router = APIRouter(prefix="/docs", dependencies=[Depends(require_addon_token)])


class AddonFinding(BaseModel):
    key: str
    comment_id: str
    quote: str
    proposed_change: str
    reason_de: str
    category: Category
    priority: Priority


class DocFindings(BaseModel):
    doc_id: str
    findings: list[AddonFinding]


def to_addon_finding(doc_id: str, open_finding: OpenFinding) -> AddonFinding:
    finding = open_finding.finding
    suggestion = finding.suggestion
    return AddonFinding(
        key=finding_key(doc_id, finding),
        comment_id=open_finding.comment_id,
        quote=suggestion.original_text,
        proposed_change=suggestion.proposed_change,
        reason_de=suggestion.reason_de,
        category=finding.category,
        priority=finding.priority,
    )


@addon_router.get("/{doc_id}/findings")
def get_doc_findings(doc_id: str, request: Request) -> DocFindings:
    container = get_container(request)
    source = container.build_comments_source()
    try:
        comments = source.read_comments(doc_id)
    except DocumentAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden oder nicht für Sophie freigegeben.",
        ) from error
    findings = findings_from_comments(comments)
    logger.info("served add-on findings", extra={"finding_count": len(findings)})
    return DocFindings(doc_id=doc_id, findings=[to_addon_finding(doc_id, of) for of in findings])
