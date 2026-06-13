from __future__ import annotations

from typing import TYPE_CHECKING, cast

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from pagedoctor.config import Settings

if TYPE_CHECKING:
    from googleapiclient._apis.docs.v1 import DocsResource
    from googleapiclient._apis.drive.v3 import DriveResource

DOCS_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
# Not drive.file: that scope cannot reach docs merely shared with the service account.
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
    credentials = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        settings.google_service_account_file, scopes=[scope]
    )
    return cast(Credentials, credentials)
