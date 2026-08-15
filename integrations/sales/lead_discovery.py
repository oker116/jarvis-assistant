import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class LeadDiscovery:
    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(db_path or root / "data" / "sales.db")

    def ingest(self, leads):
        created = []

        with sqlite3.connect(self.db_path) as con:
            for lead in leads:
                lead_id = str(lead["lead_id"])

                exists = con.execute(
                    "SELECT 1 FROM leads WHERE lead_id = ?",
                    (lead_id,)
                ).fetchone()

                now = datetime.now(timezone.utc).isoformat()

                metadata = {
                    "facebook": lead.get("facebook", {}),
                    "instagram": lead.get("instagram", {}),
                    "ads": lead.get("ads", {}),
                    "website": lead.get("website", {}),
                    "has_offer": lead.get("has_offer", False),
                    "has_whatsapp": lead.get("has_whatsapp", False),
                }

                if exists:
                    con.execute("""
                        UPDATE leads
                        SET name = ?,
                            source = ?,
                            metadata_json = ?,
                            updated_at = ?
                        WHERE lead_id = ?
                    """, (
                        lead.get("name", lead_id),
                        lead.get("source", "discovery"),
                        json.dumps(metadata, ensure_ascii=False),
                        now,
                        lead_id,
                    ))
                else:
                    con.execute("""
                        INSERT INTO leads (
                            lead_id, created_at, updated_at,
                            name, source, status, score,
                            priority, paid, revenue, metadata_json
                        )
                        VALUES (?, ?, ?, ?, ?, 'new', 0,
                                'UNKNOWN', 0, 0, ?)
                    """, (
                        lead_id,
                        now,
                        now,
                        lead.get("name", lead_id),
                        lead.get("source", "discovery"),
                        json.dumps(metadata, ensure_ascii=False),
                    ))

                created.append(lead_id)

        return created
