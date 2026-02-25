"""
Inference Logger — SQLite-backed event log for AI governance and inference tracking.

Table: inference_log
Schema:
    query_id            TEXT PRIMARY KEY
    model_version       TEXT
    user_input          TEXT
    llm_output          TEXT
    timestamp           TEXT (ISO 8601)
    latency_ms          INTEGER
    http_status         INTEGER
    evaluation_status   TEXT
    evaluation_score    REAL
    review_required     BOOLEAN
    review_outcome      TEXT
    policy_category     TEXT
    ground_truth        TEXT (partial — human-labeled reference answers)
    evaluation_timestamp TEXT (ISO 8601 — when evaluation was performed)
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit",
    "inference_audit.db",
)


class InferenceLogger:
    """SQLite logger for inference and governance events."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inference_log (
                    query_id            TEXT PRIMARY KEY,
                    model_version       TEXT,
                    user_input          TEXT,
                    llm_output          TEXT,
                    timestamp           TEXT NOT NULL,
                    latency_ms          INTEGER,
                    http_status         INTEGER,
                    evaluation_status   TEXT,
                    evaluation_score    REAL,
                    review_required     BOOLEAN,
                    review_outcome      TEXT,
                    policy_category     TEXT,
                    ground_truth        TEXT,
                    evaluation_timestamp TEXT
                )
            """)
            # Migrate: add columns if table already exists without them
            try:
                conn.execute("ALTER TABLE inference_log ADD COLUMN ground_truth TEXT")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE inference_log ADD COLUMN evaluation_timestamp TEXT")
            except Exception:
                pass

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def log_inference(
        self,
        query_id: str,
        model_version: str,
        user_input: str,
        llm_output: str,
        latency_ms: int,
        http_status: int = 200,
        evaluation_status: str = "pending",
        evaluation_score: Optional[float] = None,
        review_required: bool = False,
        review_outcome: str = "pending",
        policy_category: str = "general",
        ground_truth: Optional[str] = None,
        evaluation_timestamp: Optional[str] = None,
    ) -> None:
        """
        Log an inference event.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO inference_log
                    (query_id, model_version, user_input, llm_output, timestamp,
                     latency_ms, http_status, evaluation_status, evaluation_score,
                     review_required, review_outcome, policy_category,
                     ground_truth, evaluation_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    model_version,
                    user_input,
                    llm_output,
                    now,
                    latency_ms,
                    http_status,
                    evaluation_status,
                    evaluation_score,
                    review_required,
                    review_outcome,
                    policy_category,
                    ground_truth,
                    evaluation_timestamp,
                ),
            )
        print(f"[InferenceLog] Logged query {query_id}")

    def get_all_logs(self) -> list[dict[str, Any]]:
        """Return all inference log entries as a list of dicts."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM inference_log ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]

if __name__ == "__main__":
    logger = InferenceLogger()
    print(f"✅ Initialized inference_log table successfully at: {logger.db_path}")
