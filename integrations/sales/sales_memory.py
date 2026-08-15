import json
import os
import sqlite3
from datetime import datetime, timezone


class SalesMemory:
    """
    Permanent event store for the sales agent.
    Stores every lead, conversation event, outcome and learning signal.
    """

    def __init__(self, db_path=None):
        root_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        self.db_path = db_path or os.path.join(
            root_dir,
            "data",
            "sales.db"
        )

        os.makedirs(
            os.path.dirname(self.db_path),
            exist_ok=True
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")

            db.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    name TEXT,
                    source TEXT,
                    status TEXT,
                    score REAL DEFAULT 0,
                    priority TEXT,
                    paid INTEGER DEFAULT 0,
                    revenue REAL DEFAULT 0,
                    metadata_json TEXT
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    channel TEXT,
                    actor TEXT,
                    content TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY (lead_id)
                        REFERENCES leads(lead_id)
                        ON DELETE CASCADE
                )
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_lead
                ON events(lead_id)
            """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type)
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    revenue REAL DEFAULT 0,
                    reason TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY (lead_id)
                        REFERENCES leads(lead_id)
                        ON DELETE CASCADE
                )
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS learning_stats (
                    key TEXT PRIMARY KEY,
                    observations INTEGER DEFAULT 0,
                    successes INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    total_revenue REAL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json(data):
        return json.dumps(
            data or {},
            ensure_ascii=False
        )

    def upsert_lead(
        self,
        lead_id,
        name=None,
        source=None,
        status=None,
        score=0,
        priority=None,
        metadata=None
    ):
        now = self.now()

        with self._connect() as db:
            db.execute("""
                INSERT INTO leads (
                    lead_id,
                    created_at,
                    updated_at,
                    name,
                    source,
                    status,
                    score,
                    priority,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lead_id)
                DO UPDATE SET
                    updated_at=excluded.updated_at,
                    name=COALESCE(excluded.name, leads.name),
                    source=COALESCE(excluded.source, leads.source),
                    status=COALESCE(excluded.status, leads.status),
                    score=excluded.score,
                    priority=COALESCE(
                        excluded.priority,
                        leads.priority
                    ),
                    metadata_json=excluded.metadata_json
            """, (
                str(lead_id),
                now,
                now,
                name,
                source,
                status,
                float(score or 0),
                priority,
                self._json(metadata)
            ))

    def record_event(
        self,
        lead_id,
        event_type,
        channel=None,
        actor="jarvis",
        content=None,
        metadata=None
    ):
        with self._connect() as db:
            db.execute("""
                INSERT INTO events (
                    lead_id,
                    timestamp,
                    event_type,
                    channel,
                    actor,
                    content,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(lead_id),
                self.now(),
                event_type,
                channel,
                actor,
                content,
                self._json(metadata)
            ))

    def record_outcome(
        self,
        lead_id,
        outcome,
        revenue=0,
        reason=None,
        metadata=None
    ):
        timestamp = self.now()

        with self._connect() as db:
            db.execute("""
                INSERT INTO outcomes (
                    lead_id,
                    timestamp,
                    outcome,
                    revenue,
                    reason,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(lead_id),
                timestamp,
                outcome,
                float(revenue or 0),
                reason,
                self._json(metadata)
            ))

            paid = 1 if outcome == "paid" else 0

            db.execute("""
                UPDATE leads
                SET
                    updated_at=?,
                    status=?,
                    paid=?,
                    revenue=?
                WHERE lead_id=?
            """, (
                timestamp,
                outcome,
                paid,
                float(revenue or 0),
                str(lead_id)
            ))

    def get_events(self, lead_id):
        with self._connect() as db:
            rows = db.execute("""
                SELECT *
                FROM events
                WHERE lead_id=?
                ORDER BY timestamp ASC
            """, (str(lead_id),)).fetchall()

        return [dict(row) for row in rows]

    def get_outcomes(self):
        with self._connect() as db:
            rows = db.execute("""
                SELECT *
                FROM outcomes
                ORDER BY timestamp ASC
            """).fetchall()

        return [dict(row) for row in rows]
