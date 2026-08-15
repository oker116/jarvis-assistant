import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class OutreachQueue:

    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(
            db_path or root / "data" / "sales.db"
        )
        self._ensure_table()

    def _connect(self):
        return sqlite3.connect(str(self.db_path))

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _ensure_table(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS outreach_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    style TEXT,
                    service TEXT,
                    score REAL,
                    priority TEXT,
                    message TEXT NOT NULL,
                    evidence_json TEXT,
                    research_used INTEGER NOT NULL DEFAULT 1,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(lead_id)
                )
            """)

    def enqueue(self, result):
        if not result.get("send_allowed"):
            return {
                "queued": False,
                "reason": "send_not_allowed",
                "lead_id": result.get("lead_id"),
            }

        now = self._now()

        with self._connect() as con:
            con.execute("""
                INSERT INTO outreach_queue (
                    lead_id,
                    status,
                    style,
                    service,
                    score,
                    priority,
                    message,
                    evidence_json,
                    research_used,
                    created_at,
                    updated_at
                )
                VALUES (?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lead_id) DO UPDATE SET
                    style = excluded.style,
                    service = excluded.service,
                    score = excluded.score,
                    priority = excluded.priority,
                    message = excluded.message,
                    evidence_json = excluded.evidence_json,
                    research_used = excluded.research_used,
                    updated_at = excluded.updated_at
            """, (
                result.get("lead_id"),
                result.get("style"),
                result.get("service"),
                float(result.get("score") or 0),
                result.get("priority"),
                result.get("message") or "",
                json.dumps(
                    result.get("evidence") or [],
                    ensure_ascii=False
                ),
                1 if result.get("research_used") else 0,
                now,
                now,
            ))

        return {
            "queued": True,
            "lead_id": result.get("lead_id"),
            "style": result.get("style"),
            "score": result.get("score"),
        }

    def pending(self, limit=20):
        with self._connect() as con:
            con.row_factory = sqlite3.Row

            rows = con.execute("""
                SELECT *
                FROM outreach_queue
                WHERE status = 'queued'
                ORDER BY score DESC, id ASC
                LIMIT ?
            """, (limit,)).fetchall()

        return [dict(row) for row in rows]

    def mark_sent(self, queue_id):
        with self._connect() as con:
            con.execute("""
                UPDATE outreach_queue
                SET status = 'sent',
                    attempts = attempts + 1,
                    updated_at = ?
                WHERE id = ?
            """, (self._now(), queue_id))

    def mark_failed(self, queue_id):
        with self._connect() as con:
            con.execute("""
                UPDATE outreach_queue
                SET status = 'failed',
                    attempts = attempts + 1,
                    updated_at = ?
                WHERE id = ?
            """, (self._now(), queue_id))


if __name__ == "__main__":
    queue = OutreachQueue()

    print("Outreach Queue initialized.")
    print("Database:", queue.db_path)

    rows = queue.pending()

    print("\n=== PENDING OUTREACH ===")

    if not rows:
        print("Queue is empty.")
    else:
        for row in rows:
            print(
                f'#{row["id"]} '
                f'lead={row["lead_id"]} '
                f'score={row["score"]} '
                f'style={row["style"]}'
            )
