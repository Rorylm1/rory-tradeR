from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.paths import runtime_path
from src.trading.journal import JournalStore


def default_dashboard_db() -> Path:
    return runtime_path("dashboard", "dashboard.sqlite")


@dataclass
class LiveReviewRecord:
    proposal_id: str
    status: str
    note: str
    recorded_at: datetime


class DashboardStore:
    def __init__(self, db_path: Path | None = None, journal_path: Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_dashboard_db()
        self.journal_path = Path(journal_path) if journal_path is not None else JournalStore().path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS journal_events (
                    journal_offset INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS live_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    recorded_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_live_reviews_proposal_id ON live_reviews (proposal_id)")

    def sync_journal(self) -> int:
        events = JournalStore(path=self.journal_path).load_events()
        inserted = 0
        with self.connect() as connection:
            for offset, event in enumerate(events):
                payload_json = json.dumps(event.get("payload", {}), sort_keys=True)
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO journal_events (
                        journal_offset,
                        event_type,
                        recorded_at,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (offset, event.get("event_type", "unknown"), event.get("recorded_at", ""), payload_json),
                )
                inserted += cursor.rowcount
        return inserted

    def record_live_review(self, proposal_id: str, status: str, note: str = "") -> LiveReviewRecord:
        recorded_at = datetime.now(timezone.utc)
        note = note or ""
        JournalStore(path=self.journal_path).record_live_review(proposal_id, status, note)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO live_reviews (proposal_id, status, note, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (proposal_id, status, note, recorded_at.isoformat()),
            )
        self.sync_journal()
        return LiveReviewRecord(
            proposal_id=proposal_id,
            status=status,
            note=note,
            recorded_at=recorded_at,
        )

    def latest_live_reviews(self) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT proposal_id, status, note, recorded_at
                FROM live_reviews
                ORDER BY recorded_at ASC, id ASC
                """
            ).fetchall()

        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            latest[row["proposal_id"]] = dict(row)
        return latest
