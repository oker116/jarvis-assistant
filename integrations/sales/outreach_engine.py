import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone


class OutreachEngine:
    """
    Outbound-only sales engine.

    JARVIS can:
      - prepare an offer
      - record the offer
      - track the conversation

    JARVIS must NOT:
      - automatically reply to customer messages
      - continue a conversation automatically
    """

    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(
            db_path or root / "data" / "sales.db"
        )

    def _connect(self):
        return sqlite3.connect(str(self.db_path))

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def should_contact(self, lead):
        score = float(lead.get("score") or 0)
        status = lead.get("status", "new")

        # Don't repeatedly contact completed/lost leads.
        if status in {"won", "lost"}:
            return False

        # Only contact reasonably qualified leads.
        return score >= 60

    def build_offer(self, lead):
        name = lead.get("name") or "حضرتك"

        return (
            f"أهلًا {name}،\n\n"
            "بصيت على الـFacebook/Instagram والحضور الإعلاني "
            "والـWebsite عندكم، ولاحظت كام نقطة ممكن يكون لها "
            "تأثير مباشر على نتيجة الـMedia Buying.\n\n"
            "أقدر أعمل لكم مراجعة سريعة للحملات الحالية "
            "وأحدد أهم 3 فرص للتحسين في الإعلانات والـTracking "
            "والـLanding Page.\n\n"
            "لو مناسب، أقدر أبعتلكم التفاصيل."
        )

    def record_offer(self, lead_id, message):
        with self._connect() as con:
            con.execute(
                """
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
                """,
                (
                    lead_id,
                    self._now(),
                    "offer_sent",
                    "whatsapp",
                    "jarvis",
                    message,
                    json.dumps(
                        {
                            "mode": "outreach_only",
                            "auto_reply": False
                        },
                        ensure_ascii=False
                    )
                )
            )

            con.execute(
                """
                UPDATE leads
                SET status = 'contacted',
                    updated_at = ?
                WHERE lead_id = ?
                """,
                (self._now(), lead_id)
            )

    def prepare(self, lead):
        if not self.should_contact(lead):
            return {
                "send": False,
                "reason": "Lead does not meet outreach criteria."
            }

        message = self.build_offer(lead)

        return {
            "send": True,
            "mode": "outreach_only",
            "auto_reply": False,
            "lead_id": lead.get("lead_id"),
            "message": message
        }


if __name__ == "__main__":
    print("Outreach Engine initialized.")
    print("Mode: OUTREACH_ONLY")
    print("Auto-reply: DISABLED")
