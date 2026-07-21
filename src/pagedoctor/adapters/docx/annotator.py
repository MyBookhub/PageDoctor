import io
from collections.abc import Iterator, Sequence

from docx import Document
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from pagedoctor.domain.errors import OutputCopyError
from pagedoctor.domain.models.finding import Finding
from pagedoctor.domain.services.comment_format import format_comment_body

# The OOXML comment author is a plain string, so the imported Google Doc shows the persona
# name directly — no service-account email anywhere in the visible comment.
COMMENT_AUTHOR = "Sophie Hoffmann"
COMMENT_INITIALS = "SH"


def annotate_docx(content: bytes, findings: Sequence[Finding]) -> bytes:
    document = Document(io.BytesIO(content))
    paragraphs = list(iter_paragraphs(document))
    for finding in findings:
        runs = anchor_runs(paragraphs, finding.suggestion.original_text)
        if not runs:
            # Unlocatable quotes anchor to the document start — surfaced, never dropped;
            # the comment text still carries the exact quote so the creator can search it.
            runs = fallback_runs(paragraphs)
        if not runs:
            raise OutputCopyError("document has no text run to anchor a comment to")
        document.add_comment(
            runs=runs,
            text=format_comment_body(finding.suggestion),
            author=COMMENT_AUTHOR,
            initials=COMMENT_INITIALS,
        )
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def iter_paragraphs(document: DocumentObject) -> Iterator[Paragraph]:
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def anchor_runs(paragraphs: Sequence[Paragraph], quote: str) -> list[Run]:
    for paragraph in paragraphs:
        start = paragraph.text.find(quote)
        if start >= 0:
            return runs_covering(paragraph, start, start + len(quote))
    return []


def runs_covering(paragraph: Paragraph, start: int, end: int) -> list[Run]:
    covered: list[Run] = []
    offset = 0
    for run in paragraph.runs:
        run_end = offset + len(run.text)
        if run_end > start and offset < end:
            covered.append(run)
        offset = run_end
    return covered


def fallback_runs(paragraphs: Sequence[Paragraph]) -> list[Run]:
    for paragraph in paragraphs:
        if paragraph.runs:
            return [paragraph.runs[0]]
    return []
