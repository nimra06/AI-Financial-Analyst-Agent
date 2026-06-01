"""Background job queue persistence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from db.connection import execute, fetchall, fetchone, get_conn, init_db, is_postgres


def enqueue_job(
    job_type: str,
    payload: dict[str, Any],
    *,
    actor: Optional[str] = None,
) -> str:
    init_db()
    job_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO jobs (job_id, job_type, payload_json, status, actor, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (job_id, job_type, json.dumps(payload), actor, created),
        )
    return job_id


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        row = fetchone(
            conn,
            """
            SELECT job_id, job_type, payload_json, status, result_json, error,
                   actor, created_at, started_at, completed_at
            FROM jobs WHERE job_id = ?
            """,
            (job_id,),
        )
    if row is None:
        return None
    return _row_to_job(row)


def list_jobs(limit: int = 20, actor: Optional[str] = None) -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        if actor:
            rows = fetchall(
                conn,
                """
                SELECT job_id, job_type, payload_json, status, result_json, error,
                       actor, created_at, started_at, completed_at
                FROM jobs WHERE actor = ?
                ORDER BY id DESC LIMIT ?
                """,
                (actor, limit),
            )
        else:
            rows = fetchall(
                conn,
                """
                SELECT job_id, job_type, payload_json, status, result_json, error,
                       actor, created_at, started_at, completed_at
                FROM jobs ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            )
    return [_row_to_job(r) for r in rows]


def claim_next_job() -> Optional[dict[str, Any]]:
    """Atomically claim the oldest pending job."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        if is_postgres():
            row = fetchone(
                conn,
                """
                SELECT job_id, job_type, payload_json, status, result_json, error,
                       actor, created_at, started_at, completed_at
                FROM jobs
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
            )
            if row is None:
                return None
            execute(
                conn,
                "UPDATE jobs SET status = 'running', started_at = ? WHERE job_id = ?",
                (now, row["job_id"]),
            )
        else:
            row = fetchone(
                conn,
                """
                SELECT job_id, job_type, payload_json, status, result_json, error,
                       actor, created_at, started_at, completed_at
                FROM jobs
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT 1
                """,
            )
            if row is None:
                return None
            execute(
                conn,
                "UPDATE jobs SET status = 'running', started_at = ? WHERE job_id = ? AND status = 'pending'",
                (now, row["job_id"]),
            )
    return _row_to_job(row)


def complete_job(job_id: str, result: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        execute(
            conn,
            """
            UPDATE jobs SET status = 'completed', result_json = ?, completed_at = ?
            WHERE job_id = ?
            """,
            (json.dumps(result), now, job_id),
        )


def fail_job(job_id: str, error: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        execute(
            conn,
            """
            UPDATE jobs SET status = 'failed', error = ?, completed_at = ?
            WHERE job_id = ?
            """,
            (error[:2000], now, job_id),
        )


def _row_to_job(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "job_type": row["job_type"],
        "payload": json.loads(row["payload_json"]),
        "status": row["status"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error": row["error"],
        "actor": row["actor"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }
