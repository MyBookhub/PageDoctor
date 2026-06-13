import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from pagedoctor.app.container import get_container
from pagedoctor.app.errors import InvalidReviewForm

CSRF_SESSION_KEY = "csrf_token"

_basic = HTTPBasic(auto_error=False)


def issue_csrf(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def verify_csrf(request: Request, submitted: str) -> None:
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not secrets.compare_digest(expected, submitted):
        raise InvalidReviewForm("Sicherheitstoken ungültig. Bitte die Seite neu laden.")


def require_auth(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
) -> None:
    settings = get_container(request).settings
    user = settings.basic_auth_user
    password = settings.basic_auth_password
    if not user or password is None:
        # No shared secret configured: auth is disabled (local dev).
        return
    valid = (
        credentials is not None
        and secrets.compare_digest(credentials.username, user)
        and secrets.compare_digest(credentials.password, password.get_secret_value())
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht autorisiert",
            headers={"WWW-Authenticate": "Basic"},
        )
