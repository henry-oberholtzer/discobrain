import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from os import PathLike
from pathlib import Path
from typing import Any


class BatchStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


DEFAULT_BATCH_ID = "default"


class BatchItemStatus(StrEnum):
    PENDING = "pending"
    DROPPED = "dropped"
    SUBMITTED = "submitted"
    ERROR = "error"


@dataclass
class BatchRecord:
    id: str
    created_at: str
    status: str
    total_items: int = 0
    pending_count: int = 0
    dropped_count: int = 0
    submitted_count: int = 0
    error_count: int = 0


@dataclass
class SubmittedReleaseRecord:
    id: int
    batch_id: str
    discogs_id: int
    mbid: str | None = None
    artist: str | None = None
    title: str | None = None
    year: int | None = None
    format: str | None = None
    submitted_at: str = ""


@dataclass
class BatchItemRecord:
    id: int
    batch_id: str
    discogs_id: int
    status: str
    mbid: str | None = None
    title: str | None = None
    artist: str | None = None
    format: str | None = None
    year: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str = ""


class BatchStore:
    def __init__(self, db_path: Path | PathLike | str | None = None):
        self.db_path = str(db_path) if db_path else ":memory:"
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.init_tables()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def init_tables(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    submitted_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            try:
                self._conn.execute(
                    "ALTER TABLE batches ADD COLUMN submitted_count INTEGER NOT NULL DEFAULT 0;"
                )
            except sqlite3.OperationalError:
                pass
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    discogs_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    mbid TEXT,
                    title TEXT,
                    artist TEXT,
                    format TEXT,
                    year INTEGER,
                    payload TEXT,
                    raw_data TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
                );
                """
            )
            try:
                self._conn.execute("ALTER TABLE batch_items ADD COLUMN raw_data TEXT;")
            except sqlite3.OperationalError:
                pass
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_batch_items_batch_id ON batch_items(batch_id);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_batch_items_status ON batch_items(batch_id, status);"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS submitted_releases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    discogs_id INTEGER NOT NULL,
                    mbid TEXT,
                    artist TEXT,
                    title TEXT,
                    year INTEGER,
                    format TEXT,
                    submitted_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
                );
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_submitted_releases_batch_id ON submitted_releases(batch_id);"
            )

    def create_batch(self, batch_id: str | None = None) -> str:
        b_id = batch_id or DEFAULT_BATCH_ID
        now = self._now_iso()
        with self._conn:
            self._conn.execute(
                "INSERT INTO batches (id, created_at, status, submitted_count) VALUES (?, ?, ?, 0);",
                (b_id, now, BatchStatus.ACTIVE.value),
            )
        return b_id

    def get_or_create_batch(self, batch_id: str = DEFAULT_BATCH_ID) -> BatchRecord:
        record = self.get_batch(batch_id)
        if record is None:
            self.create_batch(batch_id)
            record = self.get_batch(batch_id)
            assert record is not None
        return record

    def add_item(
        self,
        batch_id: str,
        discogs_id: int,
        *,
        status: str = BatchItemStatus.PENDING.value,
        mbid: str | None = None,
        title: str | None = None,
        artist: str | None = None,
        format: str | None = None,
        year: int | None = None,
        payload: Mapping[str, Any] | None = None,
        raw_data: Mapping[str, Any] | None = None,
        error_message: str | None = None,
    ) -> int:
        now = self._now_iso()
        payload_json = json.dumps(payload) if payload is not None else None
        raw_data_json = json.dumps(raw_data) if raw_data is not None else None
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO batch_items (
                    batch_id, discogs_id, status, mbid, title, artist, format, year, payload, raw_data, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    batch_id,
                    discogs_id,
                    status,
                    mbid,
                    title,
                    artist,
                    format,
                    year,
                    payload_json,
                    raw_data_json,
                    error_message,
                    now,
                ),
            )
            return cursor.lastrowid or 0

    def get_batch(self, batch_id: str) -> BatchRecord | None:
        cursor = self._conn.execute(
            "SELECT id, created_at, status, submitted_count FROM batches WHERE id = ?;", (batch_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Fetch count summaries
        counts_cursor = self._conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_cnt,
                SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped_cnt,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_cnt
            FROM batch_items
            WHERE batch_id = ?;
            """,
            (batch_id,),
        )
        counts = counts_cursor.fetchone()
        row_keys = set(row.keys())
        sub_cursor = self._conn.execute(
            "SELECT COUNT(*) as sub_cnt FROM submitted_releases WHERE batch_id = ?;",
            (batch_id,),
        )
        sub_row = sub_cursor.fetchone()
        sub_table_cnt = sub_row["sub_cnt"] if sub_row else 0
        submitted = max(row["submitted_count"] if "submitted_count" in row_keys else 0, sub_table_cnt)

        return BatchRecord(
            id=row["id"],
            created_at=row["created_at"],
            status=row["status"],
            total_items=counts["total"] if counts else 0,
            pending_count=counts["pending_cnt"] if counts and counts["pending_cnt"] else 0,
            dropped_count=counts["dropped_cnt"] if counts and counts["dropped_cnt"] else 0,
            submitted_count=submitted,
            error_count=counts["error_cnt"] if counts and counts["error_cnt"] else 0,
        )

    def _row_to_item(self, row: sqlite3.Row) -> BatchItemRecord:
        payload_data = json.loads(row["payload"]) if row["payload"] else {}
        row_keys = set(row.keys())
        raw_data = (
            json.loads(row["raw_data"])
            if "raw_data" in row_keys and row["raw_data"]
            else None
        )
        return BatchItemRecord(
            id=row["id"],
            batch_id=row["batch_id"],
            discogs_id=row["discogs_id"],
            status=row["status"],
            mbid=row["mbid"],
            title=row["title"],
            artist=row["artist"],
            format=row["format"],
            year=row["year"],
            payload=payload_data,
            raw_data=raw_data,
            error_message=row["error_message"],
            created_at=row["created_at"],
        )

    def get_items(self, batch_id: str, status: str | None = None) -> list[BatchItemRecord]:
        if status:
            cursor = self._conn.execute(
                "SELECT * FROM batch_items WHERE batch_id = ? AND status = ? ORDER BY id ASC;",
                (batch_id, status),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM batch_items WHERE batch_id = ? ORDER BY id ASC;",
                (batch_id,),
            )
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def get_item(self, item_id: int) -> BatchItemRecord | None:
        cursor = self._conn.execute("SELECT * FROM batch_items WHERE id = ?;", (item_id,))
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None

    def get_item_by_discogs_id(self, batch_id: str, discogs_id: int) -> BatchItemRecord | None:
        cursor = self._conn.execute(
            "SELECT * FROM batch_items WHERE batch_id = ? AND discogs_id = ? LIMIT 1;",
            (batch_id, discogs_id),
        )
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None

    def get_next_pending_item(self, batch_id: str) -> BatchItemRecord | None:
        cursor = self._conn.execute(
            "SELECT * FROM batch_items WHERE batch_id = ? AND status = ? ORDER BY id ASC LIMIT 1;",
            (batch_id, BatchItemStatus.PENDING.value),
        )
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None

    def complete_item(self, item_id: int, mbid: str | None = None) -> None:
        with self._conn:
            cursor = self._conn.execute(
                """
                SELECT batch_id, discogs_id, mbid, title, artist, format, year
                FROM batch_items
                WHERE id = ?;
                """,
                (item_id,),
            )
            row = cursor.fetchone()
            if row:
                batch_id = row["batch_id"]
                discogs_id = row["discogs_id"]
                final_mbid = mbid if mbid is not None else row["mbid"]
                artist = row["artist"]
                title = row["title"]
                year = row["year"]
                fmt = row["format"]
                now = self._now_iso()

                self._conn.execute(
                    """
                    INSERT INTO submitted_releases (
                        batch_id, discogs_id, mbid, artist, title, year, format, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (batch_id, discogs_id, final_mbid, artist, title, year, fmt, now),
                )
                self._conn.execute(
                    "UPDATE batches SET submitted_count = submitted_count + 1 WHERE id = ?;",
                    (batch_id,),
                )
                self._conn.execute("DELETE FROM batch_items WHERE id = ?;", (item_id,))

    def record_submitted_release(
        self,
        batch_id: str,
        discogs_id: int,
        *,
        mbid: str | None = None,
        artist: str | None = None,
        title: str | None = None,
        year: int | None = None,
        format: str | None = None,
    ) -> int:
        now = self._now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO submitted_releases (
                    batch_id, discogs_id, mbid, artist, title, year, format, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (batch_id, discogs_id, mbid, artist, title, year, format, now),
            )
            self._conn.execute(
                "UPDATE batches SET submitted_count = submitted_count + 1 WHERE id = ?;",
                (batch_id,),
            )
            return cursor.lastrowid or 0

    def get_submitted_releases(
        self, batch_id: str | None = None
    ) -> list[SubmittedReleaseRecord]:
        if batch_id:
            cursor = self._conn.execute(
                """
                SELECT id, batch_id, discogs_id, mbid, artist, title, year, format, submitted_at
                FROM submitted_releases
                WHERE batch_id = ?
                ORDER BY id DESC;
                """,
                (batch_id,),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT id, batch_id, discogs_id, mbid, artist, title, year, format, submitted_at
                FROM submitted_releases
                ORDER BY id DESC;
                """
            )
        rows = cursor.fetchall()
        return [
            SubmittedReleaseRecord(
                id=r["id"],
                batch_id=r["batch_id"],
                discogs_id=r["discogs_id"],
                mbid=r["mbid"],
                artist=r["artist"],
                title=r["title"],
                year=r["year"],
                format=r["format"],
                submitted_at=r["submitted_at"],
            )
            for r in rows
        ]

    def get_total_submitted_count(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) as cnt FROM submitted_releases;")
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def delete_item(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM batch_items WHERE id = ?;", (item_id,))

    def clear_batch(self, batch_id: str = DEFAULT_BATCH_ID) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM batch_items WHERE batch_id = ?;",
                (batch_id,),
            )
            self._conn.execute(
                "UPDATE batches SET status = ? WHERE id = ?;",
                (BatchStatus.ACTIVE.value, batch_id),
            )

    def update_item_status(
        self,
        item_id: int,
        status: str,
        *,
        mbid: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status == BatchItemStatus.SUBMITTED.value:
            self.complete_item(item_id)
            return

        with self._conn:
            if mbid is not None and error_message is not None:
                self._conn.execute(
                    "UPDATE batch_items SET status = ?, mbid = ?, error_message = ? WHERE id = ?;",
                    (status, mbid, error_message, item_id),
                )
            elif mbid is not None:
                self._conn.execute(
                    "UPDATE batch_items SET status = ?, mbid = ? WHERE id = ?;",
                    (status, mbid, item_id),
                )
            elif error_message is not None:
                self._conn.execute(
                    "UPDATE batch_items SET status = ?, error_message = ? WHERE id = ?;",
                    (status, error_message, item_id),
                )
            else:
                self._conn.execute(
                    "UPDATE batch_items SET status = ? WHERE id = ?;",
                    (status, item_id),
                )

    def update_item_payload(self, item_id: int, payload: Mapping[str, Any]) -> None:
        payload_json = json.dumps(payload)
        with self._conn:
            self._conn.execute(
                "UPDATE batch_items SET payload = ? WHERE id = ?;",
                (payload_json, item_id),
            )

    def update_item_details(
        self,
        item_id: int,
        *,
        title: str | None = None,
        artist: str | None = None,
        format: str | None = None,
        year: int | None = None,
        payload: Mapping[str, Any] | None = None,
        raw_data: Mapping[str, Any] | None = None,
    ) -> None:
        payload_json = json.dumps(payload) if payload is not None else None
        raw_data_json = json.dumps(raw_data) if raw_data is not None else None
        with self._conn:
            self._conn.execute(
                """
                UPDATE batch_items
                SET title = coalesce(?, title),
                    artist = coalesce(?, artist),
                    format = coalesce(?, format),
                    year = coalesce(?, year),
                    payload = coalesce(?, payload),
                    raw_data = coalesce(?, raw_data)
                WHERE id = ?;
                """,
                (title, artist, format, year, payload_json, raw_data_json, item_id),
            )

    def update_batch_status(self, batch_id: str, status: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE batches SET status = ? WHERE id = ?;",
                (status, batch_id),
            )

    def close(self) -> None:
        self._conn.close()
