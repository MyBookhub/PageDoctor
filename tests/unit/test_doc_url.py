import pytest

from pagedoctor.app.doc_url import parse_doc_id
from pagedoctor.app.errors import InvalidReviewForm

DOC_ID = "1XRb7bVp2cxeKHI6sSY71LCBIz7-pjY0GFBghOMk6lS0"


def test_extracts_id_from_full_url() -> None:
    assert parse_doc_id(f"https://docs.google.com/document/d/{DOC_ID}/edit") == DOC_ID


def test_extracts_id_from_url_with_fragment_and_query() -> None:
    raw = f"  https://docs.google.com/document/d/{DOC_ID}/edit?usp=sharing#heading=h.x  "
    assert parse_doc_id(raw) == DOC_ID


def test_accepts_bare_id() -> None:
    assert parse_doc_id(f"  {DOC_ID}  ") == DOC_ID


def test_rejects_garbage() -> None:
    with pytest.raises(InvalidReviewForm):
        parse_doc_id("not a doc link")


def test_rejects_empty() -> None:
    with pytest.raises(InvalidReviewForm):
        parse_doc_id("   ")
