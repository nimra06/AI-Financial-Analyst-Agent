"""Persistence for upload history and chat."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from db.connection import execute, fetchall, fetchone, get_conn, init_db, is_postgres


def save_session(
    source_file: str,
    period_count: int,
    latest_month: str,
    payload: dict[str, Any],
    owner_id: Optional[str] = None,
) -> str:
    init_db()
    session_id = payload.get("session_id") or str(uuid.uuid4())
    if "session_id" not in payload:
        payload = {**payload, "session_id": session_id}
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        if is_postgres():
            execute(
                conn,
                """
                INSERT INTO sessions
                (session_id, source_file, period_count, latest_month, payload_json, owner_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    source_file = EXCLUDED.source_file,
                    period_count = EXCLUDED.period_count,
                    latest_month = EXCLUDED.latest_month,
                    payload_json = EXCLUDED.payload_json,
                    owner_id = EXCLUDED.owner_id,
                    created_at = EXCLUDED.created_at
                """,
                (
                    session_id,
                    source_file,
                    period_count,
                    latest_month,
                    json.dumps(payload),
                    owner_id,
                    created,
                ),
            )
        else:
            execute(
                conn,
                """
                INSERT OR REPLACE INTO sessions
                (session_id, source_file, period_count, latest_month, payload_json, owner_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    source_file,
                    period_count,
                    latest_month,
                    json.dumps(payload),
                    owner_id,
                    created,
                ),
            )
    return session_id


def list_sessions(limit: int = 20, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        if owner_id:
            return fetchall(
                conn,
                """
                SELECT session_id, source_file, period_count, latest_month, created_at
                FROM sessions WHERE owner_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (owner_id, limit),
            )
        return fetchall(
            conn,
            """
            SELECT session_id, source_file, period_count, latest_month, created_at
            FROM sessions ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        )


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        row = fetchone(
            conn,
            "SELECT payload_json FROM sessions WHERE session_id = ?",
            (session_id,),
        )
    if row is None:
        return None
    return json.loads(row["payload_json"])


def save_chat_message(
    session_id: str,
    role: str,
    content: str,
    sources: Optional[list[str]] = None,
) -> None:
    init_db()
    created = datetime.now(timezone.utc).isoformat()
    sources_json = json.dumps(sources) if sources else None
    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO chat_messages (session_id, role, content, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, sources_json, created),
        )


def get_chat_messages(session_id: str) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = fetchall(
            conn,
            """
            SELECT role, content, sources_json, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        sources = json.loads(row["sources_json"]) if row["sources_json"] else []
        out.append(
            {
                "role": row["role"],
                "content": row["content"],
                "sources": sources,
                "created_at": row["created_at"],
            }
        )
    return out


def clear_chat_messages(session_id: str) -> None:
    init_db()
    with get_conn() as conn:
        execute(conn, "DELETE FROM chat_messages WHERE session_id = ?", (session_id,))


def delete_session(session_id: str) -> bool:
    """Remove a dataset workspace and related chat, alerts, and scheduled reports."""
    init_db()
    with get_conn() as conn:
        row = fetchone(
            conn,
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        if row is None:
            return False
        execute(conn, "DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        execute(conn, "DELETE FROM alerts WHERE session_id = ?", (session_id,))
        execute(conn, "DELETE FROM scheduled_reports WHERE session_id = ?", (session_id,))
        cur = execute(conn, "DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return bool(getattr(cur, "rowcount", 0))
