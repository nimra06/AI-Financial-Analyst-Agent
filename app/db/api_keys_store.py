"""API key storage for B2B integrations."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from db.connection import execute, fetchall, fetchone, get_conn, init_db


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_api_key(
    label: str,
    owner_email: str,
    role: str = "Analyst",
) -> tuple[str, dict[str, Any]]:
    """Returns (raw_key, record). Raw key shown once."""
    init_db()
    raw = f"fa_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = execute(
            conn,
            """
            INSERT INTO api_keys (key_hash, key_prefix, label, owner_email, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_hash_key(raw), prefix, label, owner_email, role, created),
        )
        if hasattr(cur, "lastrowid") and cur.lastrowid:
            key_id = int(cur.lastrowid)
        else:
            row = fetchone(conn, "SELECT id FROM api_keys ORDER BY id DESC LIMIT 1")
            key_id = int(row["id"]) if row else 0
    return raw, {
        "id": key_id,
        "key_prefix": prefix,
        "label": label,
        "owner_email": owner_email,
        "role": role,
        "created_at": created,
    }


def verify_api_key(raw: str) -> Optional[dict[str, str]]:
    init_db()
    with get_conn() as conn:
        row = fetchone(
            conn,
            """
            SELECT id, label, owner_email, role
            FROM api_keys WHERE key_hash = ?
            """,
            (_hash_key(raw),),
        )
        if row is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        execute(
            conn,
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (now, row["id"]),
        )
    return {
        "actor": f"api:{row['label']} <{row['owner_email']}>",
        "role": row["role"],
        "auth_method": "api_key",
    }


def list_api_keys() -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = fetchall(
            conn,
            """
            SELECT id, key_prefix, label, owner_email, role, created_at, last_used_at
            FROM api_keys ORDER BY id DESC
            """,
        )
    return [dict(r) for r in rows]


def revoke_api_key(key_id: int) -> bool:
    init_db()
    with get_conn() as conn:
        cur = execute(conn, "DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cur.rowcount > 0
