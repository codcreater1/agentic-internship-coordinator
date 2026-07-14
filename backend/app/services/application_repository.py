"""Persistent storage for processed applications (SQLite, stdlib only).

Replaces the former in-memory list so applications survive restarts — important
once n8n is feeding applications in continuously. Each row stores the full
``ApplicationResponse`` as JSON, keyed by its stable ``id`` and ordered by
``created_at`` (newest first, matching the old ``list.insert(0)`` behaviour).
"""

from __future__ import annotations

import sqlite3
import threading

from app.core.config import settings
from app.models.application import ApplicationResponse

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id         TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                data       TEXT NOT NULL
            )
            """
        )


def add(application: ApplicationResponse) -> ApplicationResponse:
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO applications (id, created_at, data) VALUES (?, ?, ?)",
            (application.id, application.created_at, application.model_dump_json()),
        )
    return application


def update(application: ApplicationResponse) -> ApplicationResponse:
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE applications SET data = ? WHERE id = ?",
            (application.model_dump_json(), application.id),
        )
    return application


def delete(application_id: str) -> bool:
    """Remove one application by id. Returns True if a row was deleted."""
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        return cur.rowcount > 0


def list_all() -> list[ApplicationResponse]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT data FROM applications ORDER BY created_at DESC"
        ).fetchall()
    return [ApplicationResponse.model_validate_json(row["data"]) for row in rows]


def get_by_index(index: int) -> ApplicationResponse | None:
    """Position in the newest-first list — preserves the legacy index-based API."""
    if index < 0:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM applications ORDER BY created_at DESC LIMIT 1 OFFSET ?",
            (index,),
        ).fetchone()
    return ApplicationResponse.model_validate_json(row["data"]) if row else None


def get_by_id(application_id: str) -> ApplicationResponse | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
    return ApplicationResponse.model_validate_json(row["data"]) if row else None
