import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pagedoctor.app.container import get_container

_bearer = HTTPBearer(auto_error=False)


def require_addon_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    token = get_container(request).settings.addon_token
    if token is None:
        return
    valid = credentials is not None and secrets.compare_digest(
        credentials.credentials, token.get_secret_value()
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht autorisiert",
            headers={"WWW-Authenticate": "Bearer"},
        )
