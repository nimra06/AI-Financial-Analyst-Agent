"""Audit trail and retention helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from db.connection import execute, fetchall, get_conn, init_db


def log_audit_event(
    event_type: str,
    actor: str,
    *,
    session_id: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    init_db()
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO audit_events (event_type, actor, session_id, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_type,
                actor,
                session_id,
                json.dumps(detail or {}),
                created,
            ),
        )


def list_audit_events(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = fetchall(
            conn,
            """
            SELECT id, event_type, actor, session_id, detail_json, created_at
            FROM audit_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "session_id": row["session_id"],
                "detail": json.loads(row["detail_json"]) if row["detail_json"] else {},
                "created_at": row["created_at"],
            }
        )
    return out


def purge_expired_sessions(retention_days: int) -> list[str]:
    if retention_days <= 0:
        return []
    init_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    with get_conn() as conn:
        rows = fetchall(
            conn,
            "SELECT session_id FROM sessions WHERE created_at < ?",
            (cutoff,),
        )
        ids = [row["session_id"] for row in rows]
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        execute(
            conn,
            f"DELETE FROM chat_messages WHERE session_id IN ({placeholders})",
            ids,
        )
        execute(
            conn,
            f"DELETE FROM alerts WHERE session_id IN ({placeholders})",
            ids,
        )
        execute(
            conn,
            f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
            ids,
        )
    return ids


def sessions_expiring_within(days: int, retention_days: int) -> list[dict[str, Any]]:
    if retention_days <= 0:
        return []
    init_db()
    now = datetime.now(timezone.utc)
    purge_before = now - timedelta(days=retention_days - days)
    cutoff_iso = purge_before.isoformat()
    with get_conn() as conn:
        return fetchall(
            conn,
            """
            SELECT session_id, source_file, created_at
            FROM sessions
            WHERE created_at < ?
            ORDER BY created_at ASC
            """,
            (cutoff_iso,),
        )
