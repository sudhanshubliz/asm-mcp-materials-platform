from typing import Callable

from azure.identity import DefaultAzureCredential
from fastapi import Header, HTTPException, status

from app.config import config

_credential = None


def _get_credential():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_token() -> str:
    token = _get_credential().get_token("https://database.windows.net/.default")
    return token.token


def _extract_roles(x_user_roles: str | None) -> set[str]:
    if not x_user_roles:
        return set()
    return {role.strip() for role in x_user_roles.split(",") if role.strip()}


def require_authenticated_user(authorization: str | None = Header(default=None)) -> str | None:
    if not config.MCP_REQUIRE_AUTH:
        return None

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    return authorization


def require_role(required_roles: set[str]) -> Callable[[str | None], set[str]]:
    def _dependency(x_user_roles: str | None = Header(default=None)) -> set[str]:
        if not config.MCP_REQUIRE_AUTH:
            return set(config.ALLOWED_ROLES)

        roles = _extract_roles(x_user_roles)
        if not roles.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges",
            )
        return roles

    return _dependency
