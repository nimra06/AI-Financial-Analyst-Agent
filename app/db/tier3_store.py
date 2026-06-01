"""Alerts and scheduled reports persistence (Tier 3)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from db.connection import execute, fetchall, fetchone, get_conn, init_db


def _ensure_tier3_tables() -> None:
    init_db()


def replace_session_alerts(session_id: str, alerts: list[dict[str, Any]]) -> None:
    _ensure_tier3_tables()
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        execute(conn, "DELETE FROM alerts WHERE session_id = ?", (session_id,))
        for a in alerts:
            execute(
                conn,
                """
                INSERT INTO alerts
                (session_id, rule_id, severity, title, message, metric, value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    a["rule_id"],
                    a["severity"],
                    a["title"],
                    a["message"],
                    a.get("metric"),
                    a.get("value"),
                    created,
                ),
            )


def list_alerts(
    session_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    _ensure_tier3_tables()
    query = """
        SELECT id, session_id, rule_id, severity, title, message, metric, value, read_at, created_at
        FROM alerts
    """
    params: list[Any] = []
    clauses: list[str] = []
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if unread_only:
        clauses.append("read_at IS NULL")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        return fetchall(conn, query, params)


def mark_alerts_read(session_id: Optional[str] = None) -> int:
    _ensure_tier3_tables()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        if session_id:
            cur = execute(
                conn,
                "UPDATE alerts SET read_at = ? WHERE session_id = ? AND read_at IS NULL",
                (now, session_id),
            )
        else:
            cur = execute(
                conn,
                "UPDATE alerts SET read_at = ? WHERE read_at IS NULL",
                (now,),
            )
        return cur.rowcount


def create_scheduled_report(
    session_id: str,
    label: str,
    cadence: str,
    format: str,
    recipients: list[str],
) -> int:
    _ensure_tier3_tables()
    created = datetime.now(timezone.utc).isoformat()
    next_run = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    with get_conn() as conn:
        cur = execute(
            conn,
            """
            INSERT INTO scheduled_reports
            (session_id, label, cadence, format, recipients, enabled, next_run_at, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                session_id,
                label,
                cadence,
                format,
                json.dumps(recipients),
                next_run,
                created,
            ),
        )
        if hasattr(cur, "lastrowid") and cur.lastrowid:
            return int(cur.lastrowid)
        row = fetchone(conn, "SELECT id FROM scheduled_reports ORDER BY id DESC LIMIT 1")
        return int(row["id"]) if row else 0


def get_scheduled_report(report_id: int) -> Optional[dict[str, Any]]:
    _ensure_tier3_tables()
    with get_conn() as conn:
        row = fetchone(
            conn,
            """
            SELECT id, session_id, label, cadence, format, recipients, enabled,
                   last_run_at, next_run_at, created_at
            FROM scheduled_reports WHERE id = ?
            """,
            (report_id,),
        )
    if row is None:
        return None
    row["recipients"] = json.loads(row["recipients"])
    row["enabled"] = bool(row["enabled"])
    return row


def list_scheduled_reports(session_id: Optional[str] = None) -> list[dict[str, Any]]:
    _ensure_tier3_tables()
    with get_conn() as conn:
        if session_id:
            rows = fetchall(
                conn,
                """
                SELECT id, session_id, label, cadence, format, recipients, enabled,
                       last_run_at, next_run_at, created_at
                FROM scheduled_reports WHERE session_id = ?
                ORDER BY id DESC
                """,
                (session_id,),
            )
        else:
            rows = fetchall(
                conn,
                """
                SELECT id, session_id, label, cadence, format, recipients, enabled,
                       last_run_at, next_run_at, created_at
                FROM scheduled_reports ORDER BY id DESC
                """
            )
    out = []
    for row in rows:
        d = dict(row)
        d["recipients"] = json.loads(d["recipients"])
        d["enabled"] = bool(d["enabled"])
        out.append(d)
    return out


def mark_scheduled_report_run(report_id: int) -> None:
    _ensure_tier3_tables()
    now = datetime.now(timezone.utc).isoformat()
    next_run = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    with get_conn() as conn:
        execute(
            conn,
            """
            UPDATE scheduled_reports
            SET last_run_at = ?, next_run_at = ?
            WHERE id = ?
            """,
            (now, next_run, report_id),
        )


def delete_scheduled_report(report_id: int) -> bool:
    _ensure_tier3_tables()
    with get_conn() as conn:
        cur = execute(conn, "DELETE FROM scheduled_reports WHERE id = ?", (report_id,))
        return cur.rowcount > 0
