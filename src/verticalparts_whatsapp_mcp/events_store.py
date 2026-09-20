from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    idempotency_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event TEXT NOT NULL,
    record_id TEXT,
    template TEXT NOT NULL,
    numero TEXT NOT NULL,
    message_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path: Path = settings.events_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_processed(idempotency_key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        return dict(row) if row else None


def reserve(idempotency_key: str, source: str, event: str, record_id: str | None, template: str, numero: str) -> bool:
    """Tenta reservar a chave de idempotência antes de chamar a Evolution API.
    Retorna False se a chave já existe (evento já em processamento ou já processado)."""
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO events (idempotency_key, source, event, record_id, template, numero, message_id, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL, 'pending', ?)",
                (idempotency_key, source, event, record_id, template, numero, datetime.now(timezone.utc).isoformat()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def mark_done(idempotency_key: str, message_id: str | None, status: str = "sent") -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE events SET message_id = ?, status = ? WHERE idempotency_key = ?",
            (message_id, status, idempotency_key),
        )


def mark_failed(idempotency_key: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM events WHERE idempotency_key = ? AND status = 'pending'", (idempotency_key,))
