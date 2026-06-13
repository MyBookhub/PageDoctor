from __future__ import annotations

from typing import TYPE_CHECKING, cast

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from pagedoctor.config import Settings

if TYPE_CHECKING:
    from googleapiclient._apis.docs.v1 import DocsResource
    from googleapiclient._apis.drive.v3 import DriveResource

# Read-only on the manuscript; Sophie never edits text (§8).
DOCS_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
# Comment write capability. The "single-doc, never whole-Drive" guarantee (§8) is
# enforced by per-doc sharing — the service account can only touch docs explicitly
# shared with it — not by scope granularity (drive.file excludes externally-shared files).
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


def build_docs_service(settings: Settings) -> DocsResource:
    return build(
        "docs",
        "v1",
        credentials=service_account_credentials(settings, DOCS_SCOPE),
        cache_discovery=False,
    )


def build_drive_service(settings: Settings) -> DriveResource:
    return build(
        "drive",
        "v3",
        credentials=service_account_credentials(settings, DRIVE_SCOPE),
        cache_discovery=False,
    )


def service_account_credentials(settings: Settings, scope: str) -> Credentials:
    # google-auth ships an untyped signature for this classmethod; the return is typed.
    credentials = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        settings.google_service_account_file, scopes=[scope]
    )
    return cast(Credentials, credentials)
