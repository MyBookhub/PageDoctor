import re

from pagedoctor.app.errors import InvalidReviewForm

_DOC_URL = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")
_BARE_ID = re.compile(r"[a-zA-Z0-9_-]{20,}")


def parse_doc_id(raw: str) -> str:
    text = raw.strip()
    url_match = _DOC_URL.search(text)
    if url_match is not None:
        return url_match.group(1)
    if _BARE_ID.fullmatch(text) is not None:
        return text
    raise InvalidReviewForm("Bitte eine gültige Google-Docs-URL oder Dokument-ID eingeben.")
