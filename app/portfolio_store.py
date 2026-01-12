from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ContentDraft:
    draft_id: str
    snapshot_id: str | None
    topic: str
    title: str
    body: str
    disclaimer: str
    hashtags: list[str]
    created_at: str


class PortfolioStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = (
            db_path
            or os.getenv("APP_DB_PATH")
            or os.getenv("PENDING_DB_PATH")
            or "pending_actions.db"
        )
        self._init_db()

    def save_positions(
        self,
        snapshot_id: str,
        positions: list[dict[str, Any]],
    ) -> None:
        if not positions:
            return
        created_at = _now_iso()
        with self._connect() as conn:
            for position in positions:
                symbol = str(position.get("symbol", "")).strip()
                if not symbol:
                    continue
                qty = _to_float(position.get("qty"))
                if qty is None:
                    qty = 0.0
                avg_cost = _to_float(position.get("avg_cost"))
                notes = position.get("notes")
                conn.execute(
                    """
                    INSERT INTO portfolio_positions (
                        id, snapshot_id, symbol, qty, avg_cost, notes, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        snapshot_id,
                        symbol,
                        qty,
                        avg_cost,
                        str(notes) if notes is not None else None,
                        created_at,
                    ),
                )

    def save_analysis_snapshot(
        self,
        snapshot_id: str,
        trace_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        created_at = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analysis_snapshots (
                    id, trace_id, payload_json, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    trace_id,
                    json.dumps(payload, ensure_ascii=False),
                    created_at,
                ),
            )

    def save_content_draft(
        self,
        draft_id: str,
        snapshot_id: str | None,
        topic: str,
        title: str,
        body: str,
        disclaimer: str,
        hashtags: list[str],
    ) -> None:
        created_at = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO content_drafts (
                    id, snapshot_id, topic, title, body, disclaimer, hashtags_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    snapshot_id,
                    topic,
                    title,
                    body,
                    disclaimer,
                    json.dumps(hashtags, ensure_ascii=False),
                    created_at,
                ),
            )

    def fetch_latest_draft(self) -> ContentDraft | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, snapshot_id, topic, title, body, disclaimer, hashtags_json, created_at
                FROM content_drafts
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        hashtags = json.loads(row["hashtags_json"]) if row["hashtags_json"] else []
        return ContentDraft(
            draft_id=row["id"],
            snapshot_id=row["snapshot_id"],
            topic=row["topic"],
            title=row["title"],
            body=row["body"],
            disclaimer=row["disclaimer"],
            hashtags=hashtags,
            created_at=row["created_at"],
        )

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_positions (
                    id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    qty REAL NOT NULL,
                    avg_cost REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_snapshots (
                    id TEXT PRIMARY KEY,
                    trace_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_drafts (
                    id TEXT PRIMARY KEY,
                    snapshot_id TEXT,
                    topic TEXT,
                    title TEXT,
                    body TEXT,
                    disclaimer TEXT,
                    hashtags_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "portfolio_positions", "snapshot_id", "TEXT NOT NULL")
            self._ensure_column(conn, "portfolio_positions", "notes", "TEXT")
            self._ensure_column(conn, "analysis_snapshots", "trace_id", "TEXT")
            self._ensure_column(conn, "analysis_snapshots", "payload_json", "TEXT NOT NULL")
            self._ensure_column(conn, "content_drafts", "hashtags_json", "TEXT")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        name: str,
        definition: str,
    ) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row["name"] for row in rows}
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
