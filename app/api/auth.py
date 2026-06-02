"""JWT auth, Google SSO, and token helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()


class AuthError(Exception):
    pass


def create_access_token(
    *,
    name: str,
    email: str,
    role: str,
    provider: str = "demo",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "name": name,
        "email": email,
        "role": role,
        "provider": provider,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token") from exc


def claims_to_user(claims: dict[str, Any]) -> dict[str, str]:
    name = claims.get("name", "User")
    email = claims.get("email", claims.get("sub", "unknown"))
    role = claims.get("role", "Analyst")
    if role not in {"Analyst", "Admin"}:
        role = "Analyst"
    return {
        "actor": f"{name} <{email}>",
        "role": role,
        "email": email,
        "name": name,
        "auth_method": claims.get("provider", "jwt"),
    }


def verify_google_id_token(id_token: str) -> dict[str, str]:
    if not GOOGLE_CLIENT_ID:
        raise AuthError("Google SSO is not configured (GOOGLE_CLIENT_ID missing)")
    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise AuthError("Failed to verify Google token") from exc

    if data.get("aud") != GOOGLE_CLIENT_ID:
        raise AuthError("Google token audience mismatch")
    if data.get("email_verified") not in ("true", True):
        raise AuthError("Google email not verified")

    email = data.get("email", "")
    name = data.get("name") or email.split("@")[0]
    return {
        "name": name,
        "email": email,
        "role": "Analyst",
        "provider": "google",
    }
