"""FastAPI dependencies: auth, RBAC, and API keys."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from api.auth import AuthError, claims_to_user, decode_access_token
from db.api_keys_store import verify_api_key

WRITE_BLOCKED = "This action requires Analyst or Admin role."


def parse_demo_user(
    x_demo_user: Optional[str] = Header(default=None, alias="X-Demo-User"),
    x_demo_role: Optional[str] = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, str]:
    actor = (x_demo_user or "anonymous").strip() or "anonymous"
    role = (x_demo_role or "Analyst").strip()
    if role not in {"Analyst", "Admin"}:
        role = "Analyst"
    return {"actor": actor, "role": role, "auth_method": "demo"}


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_demo_user: Optional[str] = Header(default=None, alias="X-Demo-User"),
    x_demo_role: Optional[str] = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, str]:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            claims = decode_access_token(token)
            return claims_to_user(claims)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    if x_api_key:
        user = verify_api_key(x_api_key.strip())
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user

    return parse_demo_user(x_demo_user, x_demo_role)


def require_write_access(user: dict[str, str]) -> None:
    if user.get("role") not in {"Analyst", "Admin"}:
        raise HTTPException(status_code=403, detail=WRITE_BLOCKED)


def require_admin(user: dict[str, str]) -> None:
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
