"""Database connection — SQLite (local) or PostgreSQL (production)."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sessions.db"


def is_postgres() -> bool:
    return DATABASE_URL.startswith(("postgresql://", "postgres://"))


def adapt_sql(sql: str) -> str:
    if is_postgres():
        return sql.replace("?", "%s")
    return sql


def _sqlite_conn() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn() -> Iterator[Any]:
    if is_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = _sqlite_conn()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def execute(conn: Any, sql: str, params: tuple | list = ()) -> Any:
    sql = adapt_sql(sql)
    if is_postgres():
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)


def fetchall(conn: Any, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    cur = execute(conn, sql, params)
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def fetchone(conn: Any, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
    cur = execute(conn, sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def ping_db() -> bool:
    try:
        with get_conn() as conn:
            execute(conn, "SELECT 1")
        return True
    except Exception:
        return False


def _sessions_ddl() -> str:
    if is_postgres():
        return """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                period_count INTEGER NOT NULL,
                latest_month TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                owner_id TEXT,
                created_at TEXT NOT NULL
            )
        """
    return """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            source_file TEXT NOT NULL,
            period_count INTEGER NOT NULL,
            latest_month TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            owner_id TEXT,
            created_at TEXT NOT NULL
        )
    """


def _chat_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id {pk},
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources_json TEXT,
            created_at TEXT NOT NULL
        )
    """


def _audit_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS audit_events (
            id {pk},
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            session_id TEXT,
            detail_json TEXT,
            created_at TEXT NOT NULL
        )
    """


def _alerts_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS alerts (
            id {pk},
            session_id TEXT NOT NULL,
            rule_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            metric TEXT,
            value REAL,
            read_at TEXT,
            created_at TEXT NOT NULL
        )
    """


def _scheduled_reports_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS scheduled_reports (
            id {pk},
            session_id TEXT NOT NULL,
            label TEXT NOT NULL,
            cadence TEXT NOT NULL,
            format TEXT NOT NULL,
            recipients TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL
        )
    """


def _jobs_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS jobs (
            id {pk},
            job_id TEXT UNIQUE NOT NULL,
            job_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result_json TEXT,
            error TEXT,
            actor TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT
        )
    """


def _api_keys_ddl() -> str:
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
        CREATE TABLE IF NOT EXISTS api_keys (
            id {pk},
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            label TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Analyst',
            created_at TEXT NOT NULL,
            last_used_at TEXT
        )
    """


def _migrate_schema(conn: Any) -> None:
    if is_postgres():
        execute(conn, "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS owner_id TEXT")
        return
    rows = fetchall(conn, "PRAGMA table_info(sessions)")
    if not rows:
        return
    names = {row["name"] for row in rows}
    if "owner_id" not in names:
        execute(conn, "ALTER TABLE sessions ADD COLUMN owner_id TEXT")


def init_db() -> None:
    with get_conn() as conn:
        for ddl in (
            _sessions_ddl(),
            _chat_ddl(),
            _audit_ddl(),
            _alerts_ddl(),
            _scheduled_reports_ddl(),
            _jobs_ddl(),
            _api_keys_ddl(),
        ):
            execute(conn, ddl)
        _migrate_schema(conn)
        execute(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_chat_session
            ON chat_messages(session_id, id)
            """,
        )
        execute(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_status
            ON jobs(status, created_at)
            """,
        )
