from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"


@dataclass
class PendingEntry:
    pending_actions: list[dict[str, Any]]


@dataclass
class PendingActionRecord:
    action_id: str
    trace_id: str | None
    status: str
    action: dict[str, Any]
    created_at: str
    approved_by: str | None
    approved_at: str | None
    result: dict[str, Any] | None
    error: str | None


class PendingActionStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.getenv("PENDING_DB_PATH", "pending_actions.db")
        self._init_db()

    def save_pending(self, trace_id: str, pending_actions: list[dict[str, Any]]) -> None:
        if not pending_actions:
            return
        created_at = _now_iso()
        with self._connect() as conn:
            for action in pending_actions:
                action_id = str(action.get("action_id", ""))
                if not action_id:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pending_actions (
                        id, trace_id, status, action_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        trace_id,
                        STATUS_PENDING,
                        json.dumps(action),
                        created_at,
                    ),
                )

    def get_entry(self, trace_id: str) -> PendingEntry | None:
        actions = self.list_actions(trace_id)
        pending = [record.action for record in actions if record.status == STATUS_PENDING]
        if not pending:
            return None
        return PendingEntry(pending_actions=pending)

    def list_actions(self, trace_id: str) -> list[PendingActionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, trace_id, status, action_json, created_at,
                       approved_by, approved_at, result_json, error
                FROM pending_actions
                WHERE trace_id = ?
                ORDER BY created_at ASC
                """,
                (trace_id,),
            ).fetchall()
        records = []
        for row in rows:
            records.append(
                PendingActionRecord(
                    action_id=row["id"],
                    trace_id=row["trace_id"],
                    status=row["status"],
                    action=json.loads(row["action_json"]) if row["action_json"] else {},
                    created_at=row["created_at"],
                    approved_by=row["approved_by"],
                    approved_at=row["approved_at"],
                    result=json.loads(row["result_json"]) if row["result_json"] else None,
                    error=row["error"],
                )
            )
        return records

    def approve_pending(self, trace_id: str, approved_by: str) -> None:
        approved_at = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?, approved_by = ?, approved_at = ?
                WHERE trace_id = ? AND status = ?
                """,
                (STATUS_APPROVED, approved_by, approved_at, trace_id, STATUS_PENDING),
            )

    def reject_pending(self, trace_id: str, approved_by: str) -> None:
        approved_at = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?, approved_by = ?, approved_at = ?
                WHERE trace_id = ? AND status = ?
                """,
                (STATUS_REJECTED, approved_by, approved_at, trace_id, STATUS_PENDING),
            )

    def complete_action(self, action_id: str, result: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?, result_json = ?, error = NULL
                WHERE id = ?
                """,
                (STATUS_COMPLETED, json.dumps(result), action_id),
            )

    def fail_action(self, action_id: str, result: dict[str, Any], error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pending_actions
                SET status = ?, result_json = ?, error = ?
                WHERE id = ?
                """,
                (STATUS_FAILED, json.dumps(result), error, action_id),
            )

    def mark_executed(self, trace_id: str, action_id: str) -> None:
        if not trace_id or not action_id:
            return
        self.complete_action(action_id, {"tool": "", "ok": True, "output": "executed"})

    def delete(self, trace_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pending_actions WHERE trace_id = ?", (trace_id,))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id TEXT PRIMARY KEY,
                    trace_id TEXT,
                    status TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    result_json TEXT,
                    error TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
