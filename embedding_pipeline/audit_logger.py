"""
Audit Logger — SQLite-backed embedding event log for compliance.

Table: embedding_log
Fields:
    embedding_id        INTEGER PRIMARY KEY
    document_name       TEXT
    number_of_chunks    INTEGER
    date_embedded       TEXT (ISO 8601)
    policy_version      TEXT
    embedding_model_used TEXT
    collection_name     TEXT
    status              TEXT
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit",
    "embedding_audit.db",
)


class AuditLogger:
    """SQLite audit logger for embedding pipeline events."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_log (
                    embedding_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_name       TEXT NOT NULL,
                    number_of_chunks    INTEGER NOT NULL,
                    date_embedded       TEXT NOT NULL,
                    policy_version      TEXT NOT NULL,
                    embedding_model_used TEXT NOT NULL,
                    collection_name     TEXT NOT NULL,
                    status              TEXT NOT NULL DEFAULT 'success'
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def log_embedding(
        self,
        document_name: str,
        number_of_chunks: int,
        policy_version: str,
        embedding_model_used: str,
        collection_name: str,
        status: str = "success",
    ) -> int:
        """
        Log an embedding event. Returns the new embedding_id.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO embedding_log
                    (document_name, number_of_chunks, date_embedded,
                     policy_version, embedding_model_used, collection_name, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_name,
                    number_of_chunks,
                    now,
                    policy_version,
                    embedding_model_used,
                    collection_name,
                    status,
                ),
            )
            eid = cursor.lastrowid
        print(
            f"[AuditLog] Logged embedding #{eid}: "
            f"{document_name} → {number_of_chunks} chunks ({status})"
        )
        return eid  # type: ignore[return-value]

    def get_all_logs(self) -> list[dict[str, Any]]:
        """Return all audit log entries as list of dicts."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM embedding_log ORDER BY embedding_id"
            ).fetchall()
        return [dict(r) for r in rows]

    def print_audit_log(self) -> None:
        """Pretty-print the full audit log."""
        logs = self.get_all_logs()
        print(f"\n{'='*72}")
        print("  EMBEDDING AUDIT LOG")
        print(f"{'='*72}")
        if not logs:
            print("  (no entries)")
        for log in logs:
            print(
                f"  #{log['embedding_id']:>3}  "
                f"{log['document_name']:<45}  "
                f"chunks={log['number_of_chunks']:<4}  "
                f"{log['status']}"
            )
            print(
                f"       model={log['embedding_model_used']}  "
                f"ver={log['policy_version']}  "
                f"collection={log['collection_name']}  "
                f"date={log['date_embedded']}"
            )
        print(f"{'='*72}\n")
